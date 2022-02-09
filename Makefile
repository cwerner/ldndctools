NAME   := cwerner/ldndctools
TAG    := $$(git log -1 --pretty=%h)
IMG    := ${NAME}:${TAG}
LATEST := ${NAME}:latest
 
export DOCKER_BUILDKIT := 1
export $(xargs < .env)

build:
	@echo ${TAG}
	@docker build -t ${IMG} .
	@docker tag ${IMG} ${LATEST}
 
push:
	@docker push ${NAME}

run:
	@docker run --rm -p 8501:8501 --env-file .env ${LATEST} 

login:
	@docker log -u ${DOCKER_USER} -p ${DOCKER_PASS}
