# Deploy to Azure: runbook (about 40 minutes)

Easiest route: use **Azure Cloud Shell** (portal.azure.com → the `>_` icon → Bash). It already has
`az`, `terraform`, `kubectl`, `helm` and `git`, and you are already logged in, so nothing to install.
Running from your laptop works too if you install those tools and run `az login`.

## 0. Push the code to GitHub (on your laptop)
```bash
git init && git add . && git commit -m "feat: song genre predictor with MLOps pipeline"
git branch -M main
git remote add origin https://github.com/<you>/mlproject.git
git push -u origin main
```
Open the **Actions** tab and wait for the green run. It publishes the image to **GHCR**
(`ghcr.io/<you>/mlapp`). Then: your GitHub profile → **Packages** → `mlapp` → Package settings →
**Change visibility → Public**. Without this AKS cannot pull the image (`ImagePullBackOff`).

## 1. Get the code into Cloud Shell
```bash
git clone https://github.com/<you>/mlproject.git && cd mlproject
```

## 2. Check your subscription and register providers
```bash
az account show --query "{name:name, id:id}"
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.Compute
az provider register --namespace Microsoft.Network
az provider show -n Microsoft.ContainerService --query registrationState   # wait for "Registered"
```
**Azure for Students** subscriptions only allow certain regions and VM sizes. Find what you can use:
```bash
az vm list-skus --location centralindia --size Standard_B2 --query "[?restrictions==[]].name" -o tsv
```
If `Standard_B2s` is missing or the region is rejected, edit `terraform/terraform.tfvars`
(copy it from `terraform.tfvars.example`) and set `location` and `vm_size` to something allowed
(common student-friendly choices: `Standard_B2s`, `Standard_DS2_v2`, `Standard_D2s_v3`).

## 3. Create the infrastructure with Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply          # type "yes"; takes 5-10 minutes
$(terraform output -raw get_credentials_command)    # connects kubectl to the new cluster
cd ..
kubectl get nodes        # should show 1 node in Ready state
```

## 4. Deploy the app
```bash
make k8s-deploy GH_USER=<your-github-username>
kubectl get svc mlapp --watch      # wait until EXTERNAL-IP is an address, then Ctrl+C
```
Open `http://<EXTERNAL-IP>` in your browser. **That is your app running on Azure.**

## 5. Monitoring (Prometheus + Grafana)
```bash
make monitoring-install            # 2-3 minutes, check with: kubectl get pods
make k8s-monitoring
make grafana                       # prints the admin password, port-forwards to :3000
```
Cloud Shell can't open `localhost:3000` directly. Use the **Web preview** button (top bar) →
*Configure* → port **3000**. (On a laptop, open http://localhost:3000.) Log in as `admin`, go to
Dashboards → *ML App Overview*. Use the app (Predict, and upload `sample_batch.csv` in the Batch tab)
and watch the panels update.

## 6. Take your screenshots
- `kubectl get nodes,pods,svc,hpa`
- The live app on its public IP (Predict result and Model performance tab)
- Azure Portal → Resource groups → `mlproject-rg`
- `terraform apply` output
- Grafana dashboard with data
- GitHub Actions green run, and the GHCR package page

## 7. Clean up (important, AKS bills while it exists)
```bash
make tf-destroy        # type "yes". Removes the whole resource group
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| `ImagePullBackOff` | GHCR package is private or CI hasn't pushed yet. Make it public, then `kubectl rollout restart deployment/mlapp` |
| Terraform: `SkuNotAvailable` or quota error | Change `vm_size`/`location` in `terraform.tfvars` and re-run `terraform apply` |
| Terraform: `MissingSubscriptionRegistration` | Run the `az provider register` commands in step 2, wait, retry |
| `EXTERNAL-IP` stuck on `<pending>` | Wait 2-3 min, then `kubectl describe svc mlapp` |
| Grafana empty | `make k8s-monitoring` not run yet, or Prometheus target down: check Status → Targets |
| Out of time / no Azure | `docker compose up --build` shows the app + Prometheus + Grafana locally |

## Submitting to a professor without Docker
See "Sharing / submitting" in README.md: give her the live URL, repo link, screenshots/recording,
and the Docker-free `run.bat` / `run.sh`.
