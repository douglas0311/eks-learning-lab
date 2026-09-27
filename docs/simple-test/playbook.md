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

El rol propuesto es `GitHubActionsSimpleTestRole`. Se reutiliza el documento de confianza OIDC ya existente en el laboratorio, cuyo nombre contiene S3 pero cuyo contenido autoriza a GitHub a asumir un rol desde `main`. Revisa su contenido antes de usarlo: debe conservar el subject personalizado de este repositorio, no sustituirlo por un ejemplo genérico.

```bash
cat iam/github-actions-s3-trust.json
aws iam create-role --role-name GitHubActionsSimpleTestRole \
  --assume-role-policy-document file://iam/github-actions-s3-trust.json \
  --description "GitHub Actions role for simple-test deployment" \
  --profile default
aws iam put-role-policy --role-name GitHubActionsSimpleTestRole \
  --policy-name SimpleTestDeployment \
  --policy-document file://iam/simple-test-deploy-policy.json \
  --profile default
```

Si el rol ya existe, inspecciónalo antes de continuar; no intentes crearlo repetidamente. La política permite publicar en el ECR `simple-test` y describir este clúster. No permite crear ECR, EKS ni roles. `--profile default` selecciona credenciales locales; GitHub usa OIDC, sin access keys guardadas en el workflow.

## 4. Autorizar Kubernetes en cada clúster nuevo

AWS IAM y Kubernetes tienen autorizaciones diferentes. Un administrador con permisos EKS crea la entrada de acceso, que enlaza el rol con el grupo `simple-test-deployers`:

```bash
aws eks create-access-entry --cluster-name eks-learning-lab-lab-eks \
  --principal-arn arn:aws:iam::490224159848:role/GitHubActionsSimpleTestRole \
  --type STANDARD --kubernetes-groups simple-test-deployers \
  --region us-east-1 --profile default
```

Si la entrada ya existe, revísala mediante `aws eks describe-access-entry` con el mismo clúster y principal. Se requiere autenticación EKS `API` o `API_AND_CONFIG_MAP`; el Terraform del laboratorio configura esta última.

A continuación, **con una identidad que ya tenga administración en Kubernetes**, prepara el namespace y RBAC:

```bash
aws eks update-kubeconfig --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default
kubectl config current-context
kubectl auth can-i create namespaces
kubectl apply -f kubernetes/simple-test/namespace.yaml
kubectl apply -f kubernetes/simple-test/rbac.yaml
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes
```

Si `can-i` responde `no`, detente: obtener kubeconfig no concede permisos. El usuario local no necesariamente es administrador; el rol que creó el clúster tiene el acceso inicial configurado por Terraform. Debemos resolver el acceso de tu identidad antes de aplicar estos archivos. No asumas que puedes asumir ese rol desde tu usuario: su confianza OIDC puede permitir solo GitHub.

RBAC limita el workflow al namespace `simple-test`; no permite crear namespaces ni borrar recursos. La entrada de acceso, el namespace y RBAC deben recrearse después de destruir y volver a crear EKS. IAM y ECR permanecen. Metrics Server debe estar funcionando para que HPA pueda calcular CPU; CloudWatch por sí solo no lo sustituye.

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

Para retirar solo esta aplicación, una identidad administradora puede ejecutar, **después de confirmar que este namespace contiene únicamente el laboratorio**:

```bash
kubectl delete namespace simple-test
```

Esto también elimina su RBAC. Para cerrar el laboratorio completo, usa el procedimiento Terraform Decommission ya existente. El repositorio ECR y el rol preparados manualmente no pertenecen al estado Terraform y no se eliminan con ese destroy.

## Preguntas de comprobación

1. ¿Poder subir una imagen a ECR implica poder crear un Deployment?
2. ¿Qué puerto escucha Nginx y qué puerto usa la Mac con port-forward?
3. Si el HPA está sano y mantiene dos réplicas, ¿eso es un fallo?
