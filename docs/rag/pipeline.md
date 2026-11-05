# RAG por GitHub Actions

## Qué despliega
Terraform independiente: S3 fuente, S3 Vectors, ingesta PDF, consulta Titan/Nova Micro, API Gateway, CloudFront y web con evidencia recuperada. Usa nombres `rag-interview-lab-*`; no administra ni importa recursos EKS ni el RAG local anterior. Los módulos proceden del RAG local; las raíces antiguas y sus políticas para el usuario personal no se incorporan.

Dos estados remotos en el bucket existente `douglas-sre-s3-terraform-state`:
- `rag-interview/data.tfstate`: fuente versionada persistente.
- `rag-interview/terraform.tfstate`: runtime, vectores y web.

Ambos usan cifrado y bloqueo nativo S3. No crea el bucket de estado. Destruir runtime conserva PDFs y estado, pero elimina embeddings. Los documentos deben reingerirse tras recrear el índice. El smoke test lo hace explícitamente para su fixture; no reingiere todo el corpus.

## Antes de correrlo
1. Integrar esta rama en `main`. La confianza OIDC existente admite únicamente main; se preservó sin ampliarla.
2. Revisar e instalar la política adicional `iam/rag-actions-additions.json` en el rol `TerraformSRELabGitHubActionsRole`. No está aplicada automáticamente. Con una identidad autorizada, desde la raíz del repositorio:

```sh
aws iam create-policy --policy-name TerraformRAGInterview --policy-document file://iam/rag-actions-additions.json
aws iam attach-role-policy --role-name TerraformSRELabGitHubActionsRole --policy-arn arn:aws:iam::490224159848:policy/TerraformRAGInterview
```

No repetir create si la política ya existe; revisar la versión existente. El rol ya tiene IAMFullAccess: esta integración depende de ese acceso existente para roles de Lambda y PassRole y no agrega más privilegios IAM. La política adicional acota buckets, Lambda, logs y vectores por nombres. API Gateway está acotado a APIs REST de us-east-1; CloudFront usa recursos con IDs dinámicos para su ciclo de vida. No es una política exclusivamente limitada por nombre para esos dos servicios; revisar antes de instalar. Los permisos para el estado EKS no alcanzan las nuevas claves RAG.

`python3 scripts/rag/check-permissions.py` simula acciones representativas sumando la política propuesta a los permisos actuales. No instala nada ni garantiza ausencia de SCP, cuotas, restricciones de servicio o problemas en runtime.

## Ejecución manual
GitHub → Actions → **RAG Lab** → Run workflow → rama **main**.
- `plan`: valida y muestra planes; no aplica.
- `deploy`: aplica fuente y runtime, luego prueba ingesta y consulta desde CloudFront. Revisar el paso End-to-end smoke test y la URL en Summary.
- `destroy`: escribir `rag-interview` en confirm_destroy. Solo destruye runtime; conserva fuente y estado. No necesita vaciar buckets fuente ni usa estados de EKS.

No hay ejecución automática en push. El workflow RAG Checks valida PR sin credenciales AWS. No publicar planes/estados como artifacts públicos. En un fallo de persistencia se intenta guardar errored.tfstate en el prefijo privado de recuperación.

Si deploy falla después de crear recursos, puede haber infraestructura parcial. Revisar el primer fallo y ejecutar destroy manualmente con el mismo estado; no volver a aplicar a ciegas. CloudFront puede tardar en desplegar y retirarse. La fuente versionada retenida puede seguir generando cargos de almacenamiento.

## Qué prueba el smoke
Genera un PDF ficticio con una clave conocida, lo carga en S3, invoca ingesta, exige éxito de aplicación (no solo HTTP), abre la web y consulta desde `/api/query`. Exige fragmentos, generación completada y la clave en la respuesta. Los reintentos son consultas de lectura acotadas. No constituye una evaluación exhaustiva de calidad ni una prueba del corpus real.

## Límites explícitos
- Mantiene la API pública del prototipo, sin autenticación. El smoke usa únicamente datos ficticios. No cargar notas privadas de OneNote antes de resolver el control de acceso.
- Ingesta actual PDF. Markdown y sincronización OneNote/GitHub siguen pendientes y no se anuncian como implementadas.
- Gateway 29 segundos frente a Lambda 120: una consulta lenta puede fallar en el gateway y continuar en Lambda. El smoke debe detectar fallos de esta ruta; no se elevó el timeout silenciosamente.
- Logs Lambda con retención de 7 días. La correlación de éxito entre ID de API y Lambda aún no se implementa; no asumir que ambos IDs coinciden.
- Los permisos se validaron como propuesta; el primer plan/deploy desde Actions comprobará la identidad OIDC real. No se ejecutó apply durante la preparación.
