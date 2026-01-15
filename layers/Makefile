dependencies-package:
	pip install --target ./python -r ../requirements.txt &&\
	zip -r ../rule_engine_lib.zip .

upload-to-s3:
	aws s3 cp ../rule_engine_lib.zip s3://wow-lambda-package-deployments/rule_engine_lib.zip
	
all: dependencies-package upload-to-s3