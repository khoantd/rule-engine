dependencies-package:
	cd layers &&\
	pip install --target ./python -r ../requirements.txt &&\
	zip -r ../rule_engine_lib.zip . &&\
	cd ..

upload-dependencies-package-to-s3:
	aws s3 cp rule_engine_lib.zip wow-lambda-package-deployments/rule_engine_lib.zip.zip

common-package:
	zip -g wow-rule-engine-deployment-package.zip common/*.* domain/*.* services/*.* domain/conditions/*.* domain/rules/*.* domain/actions/*.*

config-package:
	zip -g wow-rule-engine-deployment-package.zip config/*.* data/input/*.*

main-package:
	zip -r wow-rule-engine-deployment-package.zip *.py

test:
	aws lambda invoke --function-name RuleEngineExecutionFn --cli-binary-format raw-in-base64-out --payload file://test-event.json response.json

deploy:
	aws lambda update-function-code --function-name RuleEngineExecutionFn --zip-file fileb://wow-rule-engine-deployment-package.zip
	
all: main-package common-package config-package deploy