# Laboratorio 02 — Pasos de activación

Esta guía prepara el ejercicio sin revelar la causa. El escenario solo se activa cuando ejecutas Update simple-test con lab-02. Provision y Deploy mantienen su comportamiento habitual.

## Qué hace cada workflow

| Workflow u opción | Cuándo usarlo | Resultado esperado |
|---|---|---|
| Terraform Provision | Cuando el clúster no existe | Infraestructura y acceso preparados; ejecución verde |
| Deploy simple-test | Después de Provision, cuando la app no existe | App instalada y validada; ejecución verde |
| Update simple-test / lab-02 | Después de comprobar que la app funciona | Aplica el incidente 02 a la app existente |
| Update simple-test / baseline | Después de documentar y acordar la solución | Restaura argumentos y recursos normales, y comprueba rollout y HTTP |
| Terraform Decommission | Al cerrar el laboratorio | Elimina infraestructura administrada y namespace de la app |

baseline no es un comando Kubernetes. Es una opción del workflow que revierte los campos modificados por estos ejercicios. Conserva la imagen existente; no es una restauración universal de cualquier cambio posible.

## Secuencia para mañana

1. Abre Actions y selecciona Terraform Provision. Ejecuta Run workflow con rama main. Espera a que termine en verde. Si falla, detente y conserva el enlace.
2. Selecciona Deploy simple-test. Ejecuta Run workflow con rama main y espera resultado verde. Este workflow no tiene el campo configuration. No uses Re-run jobs de una ejecución vieja.
3. Actualiza tu acceso local y comprueba el estado inicial:

```bash
aws sts get-caller-identity --profile default
aws eks update-kubeconfig \
  --region us-east-1 \
  --name eks-learning-lab-lab-eks \
  --profile default
kubectl -n simple-test get deployment,pods,service,hpa
```

4. Abre https://github.com/douglas0311/eks-learning-lab/actions/workflows/update-simple-test.yml. Confirma el título Update simple-test.
5. Pulsa Run workflow, rama main. En el selector de configuración elige lab-02. No elijas lab-01 ni baseline.
6. Espera: Apply selected configuration debe terminar correctamente. Verify rollout puede fallar después de varios minutos; un fallo de autenticación o de aplicación del cambio NO confirma la activación del incidente.
7. Guarda el enlace y pide: «Lab-02 activado. Dame el enunciado sin revelar la causa». Inspecciona los recursos actuales antes de concluir el impacto.

## Cómo trabajar el caso

Registra hora, alcance, evidencia, hipótesis y propuesta de validación. Puedes consultar recursos, eventos y logs según corresponda. No supongas que el síntoma tiene la misma causa que el laboratorio anterior. Evita abrir los parches del escenario antes de investigar para no adelantar la solución.

No ejecutes baseline antes de guardar la evidencia. Si necesitas cerrar por tiempo o créditos, ejecuta Terraform Decommission directamente, aunque la app esté fallando. Confirma resultado verde; si falla, podrían quedar recursos. ECR y el backend S3 persistentes no se eliminan con el clúster.

## Recuperación cuando terminemos

Ejecuta Update simple-test en main y selecciona baseline. Espera rollout y HTTP correctos. Comprueba réplicas disponibles y estado de los Pods. Si recuperas y luego quieres repetir el ejercicio, vuelve a seleccionar lab-02. No se permite activar un laboratorio sobre un rollout incompleto: restaura baseline primero o recrea el ambiente mediante el flujo habitual.

## Estado de preparación

Escenario preparado para la configuración de nodos actual del repositorio. Validado localmente como cambio de manifiestos y restauración; la activación real y sus evidencias se comprobarán en tu próxima ejecución. No se ejecutan workflows al publicar estos archivos.
