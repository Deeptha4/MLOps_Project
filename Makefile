GH_USER ?= your-github-username

.PHONY: install train test lint run docker-build up down tf-apply tf-destroy k8s-deploy monitoring-install k8s-monitoring grafana

install:
	pip install -r requirements-dev.txt

train:
	python train.py

test:
	pytest --cov=.

lint:
	ruff check .

run: train
	python serve.py

docker-build:
	docker build -t mlapp:local .

up:
	docker compose up --build

down:
	docker compose down

tf-apply:
	cd terraform && terraform init && terraform apply

tf-destroy:
	cd terraform && terraform destroy

k8s-deploy:
	sed "s|OWNER|$(shell echo $(GH_USER) | tr A-Z a-z)|" k8s/deployment.yaml | kubectl apply -f -
	kubectl apply -f k8s/service.yaml -f k8s/hpa.yaml
	kubectl rollout status deployment/mlapp
	kubectl get pods,svc

monitoring-install:
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update
	helm upgrade --install monitoring prometheus-community/kube-prometheus-stack

k8s-monitoring:
	kubectl apply -f k8s/monitoring.yaml
	kubectl create configmap mlapp-dashboard \
		--from-file=monitoring/grafana/dashboards/ml-dashboard.json \
		--dry-run=client -o yaml | kubectl label --local -f - grafana_dashboard=1 -o yaml | kubectl apply -f -

grafana:
	@echo "Password:" && kubectl get secret monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 -d && echo
	kubectl port-forward svc/monitoring-grafana 3000:80
