#!/bin/bash
#
# Simple Docker image building script for Rule Engine
#
# Usage:
#   ./build-image.sh [--platform PLATFORM] [--registry REGISTRY] [--push]
#
# Arguments:
#   --platform PLATFORM   Platform(s) to build for (e.g., linux/amd64, linux/arm64, or linux/amd64,linux/arm64)
#   --registry REGISTRY   Docker registry URL (e.g., docker.io/khoa0702 or myregistry.io)
#   --push                Push image to registry after building
#
# Examples:
#   ./build-image.sh
#   ./build-image.sh --platform linux/amd64
#   ./build-image.sh --registry docker.io/khoa0702 --push
#   ./build-image.sh --platform linux/amd64,linux/arm64 --registry docker.io/khoa0702 --push
#

set -e

# Default values
IMAGE_NAME="khoa0702/rule-engine"
IMAGE_TAG="latest"
FULL_TAG="${IMAGE_NAME}:${IMAGE_TAG}"
PLATFORM=""
REGISTRY=""
PUSH=false
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
Simple Docker image building script for Rule Engine

Usage:
    $0 [--platform PLATFORM] [--registry REGISTRY] [--push]

Arguments:
    --platform PLATFORM   Platform(s) to build for
                          Examples: linux/amd64, linux/arm64, linux/amd64,linux/arm64
                          If not specified, builds for the native platform
    --registry REGISTRY    Full Docker image path (registry/namespace/image-name)
                          Examples: khoa0702/rule-engine, docker.io/khoa0702/rule-engine, ghcr.io/username/rule-engine
                          If not specified, builds locally only (default: khoa0702/rule-engine)
    --push                Push image to registry after building
                          Requires --registry to be set

Examples:
    $0
    $0 --platform linux/amd64
    $0 --registry docker.io/khoa0702 --push
    $0 --platform linux/amd64,linux/arm64 --registry docker.io/khoa0702 --push
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM="$2"
            USE_BUILDX=true
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --push)
            PUSH=true
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

# Validate arguments
if [[ "$PUSH" == true ]] && [[ -z "$REGISTRY" ]]; then
    print_error " --push requires --registry to be set"
    exit 1
fi

# Validate Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Setup buildx if platform is specified or pushing is requested
if [[ "$USE_BUILDX" == true ]] || [[ "$PUSH" == true ]]; then
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
        if [[ "$PUSH" == true ]]; then
            print_warn "Using regular docker push (buildx recommended for multi-platform builds)"
        fi
        USE_BUILDX=false
    fi
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Determine final image tag
if [[ -n "$REGISTRY" ]]; then
    # Remove trailing slash from registry if present
    REGISTRY="${REGISTRY%/}"
    # Use registry directly as the full image path (e.g., "khoa0702/rule-engine" becomes "khoa0702/rule-engine:latest")
    FINAL_TAG="${REGISTRY}:${IMAGE_TAG}"
else
    FINAL_TAG="$FULL_TAG"
fi

# Print build information
print_info "Building Docker image: ${FINAL_TAG}"
print_info "Project root: ${PROJECT_ROOT}"
if [[ -n "$PLATFORM" ]]; then
    print_info "Platform(s): ${PLATFORM}"
fi
if [[ -n "$REGISTRY" ]]; then
    print_info "Registry: ${REGISTRY}"
fi
if [[ "$PUSH" == true ]]; then
    print_info "Will push to registry after build"
fi
print_info "Using buildx: ${USE_BUILDX}"

# Build arguments
BUILD_ARGS=(
    -t "$FINAL_TAG"
)

# Add platform if specified
if [[ -n "$PLATFORM" ]]; then
    BUILD_ARGS+=(--platform "$PLATFORM")
fi

# Handle building and pushing
if [[ "$PUSH" == true ]] && [[ "$USE_BUILDX" == true ]]; then
    # Build and push in one step with buildx
    print_info "Building and pushing image to registry: ${FINAL_TAG}"
    
    PUSH_BUILD_ARGS=(
        -t "$FINAL_TAG"
        --push
    )
    
    # Add platform if specified
    if [[ -n "$PLATFORM" ]]; then
        PUSH_BUILD_ARGS+=(--platform "$PLATFORM")
    fi
    
    print_info "Starting Docker buildx build and push..."
    if docker buildx build "${PUSH_BUILD_ARGS[@]}" "$PROJECT_ROOT"; then
        print_info "Successfully built and pushed image: ${FINAL_TAG}"
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
            print_info "Successfully built image: ${FINAL_TAG}"
        else
            print_error "Failed to build Docker image"
            exit 1
        fi
    else
        # Use regular docker build
        if docker build "${BUILD_ARGS[@]}" "$PROJECT_ROOT"; then
            print_info "Successfully built image: ${FINAL_TAG}"
        else
            print_error "Failed to build Docker image"
            exit 1
        fi
    fi
    
    # Push with regular docker push (if requested and not using buildx)
    if [[ "$PUSH" == true ]] && [[ "$USE_BUILDX" == false ]]; then
        print_info "Pushing image to registry: ${FINAL_TAG}"
        if docker push "$FINAL_TAG"; then
            print_info "Successfully pushed image: ${FINAL_TAG}"
        else
            print_error "Failed to push image to registry"
            exit 1
        fi
    fi
fi

# Print summary
echo ""
print_info "Build completed successfully!"
print_info "Image: ${FINAL_TAG}"
if [[ "$PUSH" == false ]] && [[ -n "$REGISTRY" ]]; then
    print_info ""
    print_info "To push the image, run:"
    print_info "  docker push ${FINAL_TAG}"
fi
print_info ""
print_info "To run the container:"
print_info "  docker run -p 8000:8000 ${FINAL_TAG}"
print_info ""
print_info "To run with environment variables:"
print_info "  docker run -p 8000:8000 -e API_PORT=8000 -e LOG_LEVEL=INFO ${FINAL_TAG}"
print_info ""
