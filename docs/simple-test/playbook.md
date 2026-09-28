# Playbook: simple-test en EKS

Este laboratorio prepara una página HTML servida por Nginx en un contenedor, publica su imagen en ECR y la despliega mediante GitHub Actions. Los comandos siguientes son para ejecutarlos por etapas; la preparación local no crea recursos en AWS.

## 1. Archivos y propósito

| Archivo/directorio | Propósito |
|---|---|
| `application/simple-test/` | HTML, configuración Nginx y Dockerfile |
| `kubernetes/simple-test/` | Deployment, Service, HPA y preparación de namespace/RBAC |
| `iam/simple-test-deploy-policy.json` | Permisos AWS del rol de despliegue |
| `.github/workflows/deploy-simple-test.yml` | Construcción, prueba, publicación y despliegue inicial |

El nombre del clúster configurado en este repositorio es **eks-learning-lab-lab-eks**, región **us-east-1**, cuenta **490224159848**. Confirma que Terraform Provision terminó correctamente antes de continuar. El workflow no crea el clúster ni el repositorio ECR.

```bash
cd /Users/douglasgarcia/Documents/GitHub/terraform
aws sts get-caller-identity --profile default
aws eks describe-cluster --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default \
  --query 'cluster.{Name:name,Status:status,Version:version}'
```

## 2. Preparar ECR una vez

Comprueba si el repositorio ya existe. Solo un error `RepositoryNotFoundException` indica que corresponde crearlo; errores de autenticación o permisos deben resolverse primero.

```bash
aws ecr describe-repositories --repository-names simple-test \
  --region us-east-1 --profile default
```

Si no existe:

```bash
aws ecr create-repository --repository-name simple-test \
  --image-tag-mutability IMMUTABLE \
  --encryption-configuration encryptionType=AES256 \
  --region us-east-1 --profile default
```

Las etiquetas inmutables impiden sobrescribir una etiqueta existente. El workflow usa commit, ejecución e intento para generar una etiqueta única; Kubernetes recibe el digest de la imagen. ECR persiste después de destruir EKS y sus imágenes pueden generar cargos de almacenamiento. Esta primera versión no configura limpieza automática de imágenes.

## 3. Preparar el rol AWS una vez

El rol es `GitHubActionsSimpleTestRole`. Su documento de confianza OIDC dedicado permite a GitHub asumirlo desde `main` de este repositorio. Conserva el subject personalizado; no lo sustituyas por un ejemplo genérico. ECR y este rol ya fueron creados durante la preparación inicial; los comandos de creación se conservan como referencia para una cuenta nueva.

```bash
cat iam/simple-test-trust.json
aws iam create-role --role-name GitHubActionsSimpleTestRole \
  --assume-role-policy-document file://iam/simple-test-trust.json \
  --description "GitHub Actions role for simple-test deployment" \
  --profile default
aws iam put-role-policy --role-name GitHubActionsSimpleTestRole \
  --policy-name SimpleTestDeployment \
  --policy-document file://iam/simple-test-deploy-policy.json \
  --profile default
```

Si el rol ya existe, inspecciónalo antes de continuar; no intentes crearlo repetidamente. La política permite publicar en el ECR `simple-test` y describir este clúster. No permite crear ECR, EKS ni roles. `--profile default` selecciona credenciales locales; GitHub usa OIDC, sin access keys guardadas en el workflow.

## 4. Preparación automática del clúster

`simple-test-access.tf` declara cuatro recursos que **Terraform Provision** prepara en cada clúster:

- Entrada EKS para `GitHubActionsSimpleTestRole`, vinculada al grupo `simple-test-deployers`.
- Namespace `simple-test`.
- Role con permisos para instalar y consultar esta aplicación.
- RoleBinding que conecta el grupo con el Role.

Terraform lee las reglas desde `kubernetes/simple-test/rbac.yaml`. No apliques esos manifiestos manualmente después: Terraform administra esta preparación. El Deployment, Service y HPA pertenecen al job de la aplicación.

El rol de Provision necesita la política adicional siguiente. Ya se aplicó durante la preparación inicial; el comando sirve de referencia:

```bash
aws iam put-role-policy --role-name TerraformSRELabGitHubActionsRole \
  --policy-name TerraformSimpleTestAccess \
  --policy-document file://iam/simple-test-bootstrap-policy.json \
  --profile default
```

Esta política limita la creación de entradas al rol de simple-test en este clúster. No concede acceso Kubernetes directamente: la entrada EKS y el RoleBinding deben existir también.

**Orden para el clúster actual:** publica los cambios, ejecuta Terraform Provision y espera que termine correctamente; después ejecuta Deploy simple-test. No hace falta Decommission para añadir estos cuatro recursos al clúster que ya funciona. Revisa el plan: si aparecen cambios no esperados, detente para investigarlos.

En futuros laboratorios: Provision reconstruye namespace/RBAC/entrada EKS; ECR y el rol IAM persisten. Metrics Server debe estar funcionando para que el HPA calcule CPU.

Con tu usuario de diagnóstico puedes verificar la preparación:

```bash
kubectl get namespace simple-test
kubectl -n simple-test get role,rolebinding
```

## 5. Prueba local opcional del contenedor

Con Docker funcionando:

```bash
docker build --platform linux/amd64 -t simple-test:local application/simple-test
docker run --rm -d --name simple-test-local \
  --read-only --tmpfs /tmp:rw,size=33554432,mode=1777 \
  --cap-drop ALL --security-opt no-new-privileges \
  --sysctl net.ipv4.ip_unprivileged_port_start=0 \
  --memory 64m --cpus 0.1 \
  -p 127.0.0.1:8080:80 simple-test:local
curl --fail http://localhost:8080/healthz
curl --fail http://localhost:8080/
docker stop simple-test-local
```

La imagen se construye para los nodos AMD64 del laboratorio. Una Mac ARM necesita emulación para esta prueba. El contenedor escucha en 80; el puerto 8080 pertenece a la Mac.

## 6. Revisar y subir a Git

Primero termina o separa los cambios anteriores de Terraform: `git commit` incluye **todos** los archivos staged. No uses `git add .` porque el repositorio contiene otros laboratorios.

```bash
git status --short
git diff --cached --name-only
```

Cuando el staging anterior esté resuelto:

```bash
git add application/simple-test/ kubernetes/simple-test/ \
  .github/workflows/deploy-simple-test.yml \
  iam/simple-test-deploy-policy.json docs/simple-test/
git diff --cached --stat
git diff --cached
git commit -m "Add simple-test EKS application and deployment workflow"
git push origin main
```

Estos comandos se ejecutan solo cuando decidas publicar el cambio. El workflow manual debe estar en la rama por defecto para aparecer en Actions. La confianza OIDC actual autoriza `main`.

## 7. Ejecutar el workflow inicial

En GitHub: **Actions → Deploy simple-test → Run workflow → main**.

El job verifica cuenta, clúster activo, ECR inmutable, permisos Kubernetes y API de métricas. Después construye y prueba el contenedor, publica la imagen, valida los manifiestos contra el API server y los aplica. Espera el rollout y un HPA con `ScalingActive`, y prueba HTTP mediante port-forward.

Si falta ECR, el clúster o sus permisos, se detiene. Si ya existe el Deployment `simple-test`, también se detiene: el job para actualizar la aplicación será el siguiente laboratorio. Comparte el grupo de concurrencia de Terraform para evitar que estos workflows se ejecuten simultáneamente; operaciones manuales externas no quedan bloqueadas por ese mecanismo.

Un fallo puede dejar recursos parciales e imágenes publicadas. Se conservan para diagnóstico, sin rollback automático. Si ya se creó el Deployment, un reintento se detendrá por existencia: revisa primero el problema y decide la recuperación. No borres recursos para ocultar el fallo.

## 8. Validación y acceso

```bash
kubectl -n simple-test get deployment,pods,service,hpa
kubectl -n simple-test top pods
kubectl -n simple-test describe hpa simple-test
kubectl -n simple-test port-forward service/simple-test 8080:80
```

Mantén el último comando abierto y usa `http://localhost:8080` en la Mac. Esto crea un túnel autenticado; no publica la aplicación en Internet. La prueba del workflow también usa un túnel y verifica un Pod seleccionado, no toda la ruta ClusterIP.

Para probar DNS y Service desde dentro del clúster, una identidad con permiso de crear Pods puede ejecutar:

```bash
kubectl -n simple-test run simple-test-client --rm -i --restart=Never \
  --image=busybox:1.37 -- wget -qO- http://simple-test.simple-test.svc.cluster.local:80
```

El rol del workflow no tiene permiso de crear Pods directamente. Un cliente de prueba necesita además poder descargar su imagen. Con poco tráfico, dos réplicas y un HPA activo son un resultado correcto; no esperamos cuatro réplicas permanentemente.

## 9. Diagnóstico y cierre

```bash
kubectl -n simple-test get events --sort-by=.lastTimestamp
kubectl -n simple-test describe deployment simple-test
kubectl -n simple-test logs deployment/simple-test --tail=100
kubectl -n simple-test describe hpa simple-test
```

`ImagePullBackOff`: comprueba imagen y permiso ECR del rol de los nodos. `Pending`: revisa capacidad y eventos. HPA con métricas desconocidas: revisa Metrics Server, requests y Pods Ready. `Forbidden`: revisa identidad, entrada de acceso y RBAC.

Para retirar solo esta aplicación, una identidad administradora puede ejecutar desde la raíz del repositorio:

```bash
kubectl delete -k kubernetes/simple-test
```

Esto elimina Deployment, Service y HPA, conservando el namespace y RBAC administrados por Terraform. Tu usuario de diagnóstico tiene acceso de lectura, por lo que no puede ejecutar esta eliminación. Para cerrar el laboratorio completo, usa Terraform Decommission; este también elimina el namespace/RBAC y la entrada de acceso del rol de la app. El repositorio ECR y el rol preparados manualmente no pertenecen al estado Terraform y no se eliminan con ese destroy.

## Preguntas de comprobación

1. ¿Poder subir una imagen a ECR implica poder crear un Deployment?
2. ¿Qué puerto escucha Nginx y qué puerto usa la Mac con port-forward?
3. Si el HPA está sano y mantiene dos réplicas, ¿eso es un fallo?
