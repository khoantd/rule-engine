#!/bin/bash
#
# Build script for Rule Engine Docker image
#
# Usage:
#   ./build-docker-image.sh [OPTIONS]
#
# Options:
#   -t, --tag TAG          Tag for the image (default: rule-engine:latest)
#   -v, --version VERSION Version tag for the image (optional)
#   -n, --name NAME       Image name (default: rule-engine)
#   -p, --platform PLATFORM Platform(s) to build for (e.g., linux/amd64, linux/arm64, or linux/amd64,linux/arm64)
#   --no-cache            Build without cache
#   --push                Push image to registry (requires DOCKER_REGISTRY env var)
#   -h, --help            Show this help message
#
# Examples:
#   ./build-docker-image.sh
#   ./build-docker-image.sh -t rule-engine:1.0.0
#   ./build-docker-image.sh -v 1.0.0 --push
#   ./build-docker-image.sh -p linux/amd64
#   ./build-docker-image.sh -p linux/amd64,linux/arm64 --push
#   DOCKER_REGISTRY=myregistry.io ./build-docker-image.sh -v 1.0.0 -p linux/amd64 --push
#

set -e

# Default values
IMAGE_NAME="khoa0702/rule-engine"
IMAGE_TAG="latest"
FULL_TAG="${IMAGE_NAME}:${IMAGE_TAG}"
USE_CACHE=true
PUSH_IMAGE=false
PLATFORM=""
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
USE_BUILDX=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show help
show_help() {
    cat << EOF
Build script for Rule Engine Docker image

Usage:
    $0 [OPTIONS]

Options:
    -t, --tag TAG          Tag for the image (default: rule-engine:latest)
    -v, --version VERSION  Version tag for the image (optional)
    -n, --name NAME        Image name (default: rule-engine)
    -p, --platform PLATFORM Platform(s) to build for
                           Examples: linux/amd64, linux/arm64, linux/amd64,linux/arm64
                           If not specified, builds for the native platform
    --no-cache             Build without cache
    --push                 Push image to registry (requires DOCKER_REGISTRY env var)
    -h, --help             Show this help message

Examples:
    $0
    $0 -t rule-engine:1.0.0
    $0 -v 1.0.0 --push
    $0 -p linux/amd64
    $0 -p linux/amd64,linux/arm64 --push
    DOCKER_REGISTRY=myregistry.io $0 -v 1.0.0 -p linux/amd64 --push
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            FULL_TAG="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            if [[ -n "$VERSION" ]]; then
                IMAGE_TAG="$VERSION"
                FULL_TAG="${IMAGE_NAME}:${VERSION}"
            fi
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            FULL_TAG="${IMAGE_NAME}:${IMAGE_TAG}"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            USE_BUILDX=true
            shift 2
            ;;
        --no-cache)
            USE_CACHE=false
            shift
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Setup buildx if platform is specified or pushing is requested
if [[ "$USE_BUILDX" == true ]] || [[ "$PUSH_IMAGE" == true ]]; then
    # Check if buildx is available
    if docker buildx version &> /dev/null; then
        USE_BUILDX=true
        # Create builder instance if it doesn't exist
        BUILDER_NAME="rule-engine-builder"
        if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
            print_info "Creating buildx builder instance: ${BUILDER_NAME}"
            docker buildx create --name "$BUILDER_NAME" --use --bootstrap || {
                print_warn "Failed to create buildx builder, using default"
                BUILDER_NAME="default"
            }
        else
            print_info "Using buildx builder: ${BUILDER_NAME}"
            docker buildx use "$BUILDER_NAME" || {
                print_warn "Failed to use buildx builder, using default"
                BUILDER_NAME="default"
            }
        fi
    else
        print_warn "docker buildx is not available"
        if [[ -n "$PLATFORM" ]]; then
            print_warn "Platform specification requires buildx. Falling back to regular docker build."
            print_warn "Platform specification ignored without buildx"
            PLATFORM=""
        fi
        if [[ "$PUSH_IMAGE" == true ]]; then
            print_warn "Using regular docker push (buildx recommended for multi-platform builds)"
        fi
        USE_BUILDX=false
    fi
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Print build information
print_info "Building Docker image: ${FULL_TAG}"
print_info "Project root: ${PROJECT_ROOT}"
print_info "Using cache: ${USE_CACHE}"
if [[ -n "$PLATFORM" ]]; then
    print_info "Platform(s): ${PLATFORM}"
fi
print_info "Using buildx: ${USE_BUILDX}"

# Build arguments
BUILD_ARGS=(
    -t "$FULL_TAG"
)

# Add platform if specified
if [[ -n "$PLATFORM" ]]; then
    BUILD_ARGS+=(--platform "$PLATFORM")
fi

# Add --no-cache if requested
if [[ "$USE_CACHE" == false ]]; then
    BUILD_ARGS+=(--no-cache)
fi

# Handle building and pushing
if [[ "$PUSH_IMAGE" == true ]] && [[ "$USE_BUILDX" == true ]]; then
    # Build and push in one step with buildx
    if [[ -z "$DOCKER_REGISTRY" ]]; then
        print_error "DOCKER_REGISTRY environment variable is not set"
        print_error "Please set it before using --push option"
        exit 1
    fi
    
    REGISTRY_TAG="${DOCKER_REGISTRY}/${FULL_TAG}"
    print_info "Building and pushing image to registry: ${REGISTRY_TAG}"
    
    # Build and push with buildx
    PUSH_BUILD_ARGS=(
        -t "$REGISTRY_TAG"
        --push
    )
    
    # Add platform if specified
    if [[ -n "$PLATFORM" ]]; then
        PUSH_BUILD_ARGS+=(--platform "$PLATFORM")
    fi
    
    # Add --no-cache if requested
    if [[ "$USE_CACHE" == false ]]; then
        PUSH_BUILD_ARGS+=(--no-cache)
    fi
    
    print_info "Starting Docker buildx build and push..."
    if docker buildx build "${PUSH_BUILD_ARGS[@]}" "$PROJECT_ROOT"; then
        print_info "Successfully built and pushed image: ${REGISTRY_TAG}"
        
        # Also push latest tag if version was specified
        if [[ -n "$VERSION" && "$VERSION" != "latest" ]]; then
            LATEST_REGISTRY_TAG="${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"
            print_info "Building and pushing latest tag: ${LATEST_REGISTRY_TAG}"
            LATEST_PUSH_ARGS=(
                -t "$LATEST_REGISTRY_TAG"
                --push
            )
            if [[ -n "$PLATFORM" ]]; then
                LATEST_PUSH_ARGS+=(--platform "$PLATFORM")
            fi
            if [[ "$USE_CACHE" == false ]]; then
                LATEST_PUSH_ARGS+=(--no-cache)
            fi
            if docker buildx build "${LATEST_PUSH_ARGS[@]}" "$PROJECT_ROOT"; then
                print_info "Successfully pushed latest tag: ${LATEST_REGISTRY_TAG}"
            else
                print_warn "Failed to push latest tag"
            fi
        fi
    else
        print_error "Failed to build and push image to registry"
        exit 1
    fi
else
    # Build locally (without pushing)
    
    # Add --load flag for single platform builds with buildx (required to load into local docker)
    if [[ "$USE_BUILDX" == true ]]; then
        # Only use --load for single platform builds
        if [[ -z "$PLATFORM" ]] || [[ "$PLATFORM" != *","* ]]; then
            BUILD_ARGS+=(--load)
        else
            print_warn "Multi-platform build detected. Use --push to push to registry."
            print_warn "Local docker daemon doesn't support multi-platform images directly."
        fi
    fi
    
    # Build the image
    print_info "Starting Docker build..."
    if [[ "$USE_BUILDX" == true ]]; then
        # Use buildx for platform-specific builds
        if docker buildx build "${BUILD_ARGS[@]}" "$PROJECT_ROOT"; then
            print_info "Successfully built image: ${FULL_TAG}"
        else
            print_error "Failed to build Docker image"
            exit 1
        fi
    else
        # Use regular docker build
        if docker build "${BUILD_ARGS[@]}" "$PROJECT_ROOT"; then
            print_info "Successfully built image: ${FULL_TAG}"
        else
            print_error "Failed to build Docker image"
            exit 1
        fi
    fi
    
    # Push with regular docker push (if requested and not using buildx)
    if [[ "$PUSH_IMAGE" == true ]] && [[ "$USE_BUILDX" == false ]]; then
        if [[ -z "$DOCKER_REGISTRY" ]]; then
            print_error "DOCKER_REGISTRY environment variable is not set"
            print_error "Please set it before using --push option"
            exit 1
        fi
        
        REGISTRY_TAG="${DOCKER_REGISTRY}/${FULL_TAG}"
        print_info "Tagging for registry: ${REGISTRY_TAG}"
        docker tag "$FULL_TAG" "$REGISTRY_TAG"
        
        print_info "Pushing image to registry: ${REGISTRY_TAG}"
        if docker push "$REGISTRY_TAG"; then
            print_info "Successfully pushed image: ${REGISTRY_TAG}"
            
            # Also push latest tag if version was specified
            if [[ -n "$VERSION" && "$VERSION" != "latest" ]]; then
                LATEST_REGISTRY_TAG="${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"
                docker tag "$FULL_TAG" "$LATEST_REGISTRY_TAG"
                docker push "$LATEST_REGISTRY_TAG"
                print_info "Successfully pushed latest tag: ${LATEST_REGISTRY_TAG}"
            fi
        else
            print_error "Failed to push image to registry"
            exit 1
        fi
    else
        # Tag as latest if version was specified (only for local builds with single platform)
        if [[ -n "$VERSION" && "$VERSION" != "latest" ]]; then
            # Only tag locally if not using buildx or if it's a single platform build
            if [[ "$USE_BUILDX" == false ]] || ([[ "$USE_BUILDX" == true ]] && ([[ -z "$PLATFORM" ]] || [[ "$PLATFORM" != *","* ]])); then
                LATEST_TAG="${IMAGE_NAME}:latest"
                print_info "Tagging as latest: ${LATEST_TAG}"
                docker tag "$FULL_TAG" "$LATEST_TAG"
            fi
        fi
    fi
fi

# Print summary
echo ""
print_info "Build completed successfully!"
print_info "Image: ${FULL_TAG}"
print_info ""
print_info "To run the container:"
print_info "  docker run -p 8000:8000 ${FULL_TAG}"
print_info ""
print_info "To run with environment variables:"
print_info "  docker run -p 8000:8000 -e API_PORT=8000 -e LOG_LEVEL=INFO ${FULL_TAG}"
print_info ""

