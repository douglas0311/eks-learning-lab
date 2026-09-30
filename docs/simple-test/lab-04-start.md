# Laboratorio 04 — Conectividad de la aplicación

## Objetivo

Investigar un incidente de acceso interno a simple-test y contrastar Kubernetes, observabilidad y una prueba de cliente. El ejercicio mantiene acceso privado: no crea Ingress, ALB, NLB ni DNS público. La causa concreta se descubre durante la investigación.

## Pasos para mañana

Ejecuta cada workflow desde main y espera su resultado antes del siguiente:

1. Terraform Provision: recrea el clúster y los permisos. Espera verde.
2. Deploy simple-test: instala la aplicación sana. Espera verde. Si ya existe por una ejecución interrumpida, valida el estado con el flujo de recuperación correspondiente antes de continuar.
3. Configure SRE observability: prepara el dashboard y las alertas. Espera verde.
4. Abre Grafana, guarda una captura del estado sano y anota la hora.
5. Abre Run SRE lab 04 y selecciona operation activate. No se activa mediante Update simple-test ni Run SRE lab 03.
6. Espera verde: significa que se comprobó el funcionamiento previo y luego el síntoma del incidente, no que el servicio esté sano.
7. Comparte el enlace y pide: «Dame el enunciado de lab-04 sin revelar la causa».

Workflow: https://github.com/douglas0311/eks-learning-lab/actions/workflows/run-sre-lab-04.yml

## Qué hace cada opción

| Opción | Cuándo usarla | Qué significa verde |
|---|---|---|
| activate | Una sola vez, después de la base sana | Incidente aplicado y síntoma verificado |
| check | Para comprobar acceso durante la investigación | DNS y HTTP interno respondieron correctamente |
| restore | Después de guardar evidencia y acordar la solución | Configuración original restaurada, rollout y HTTP interno correctos |

check no modifica el Deployment ni el Service. Crea un Pod de prueba temporal y lo elimina al terminar. Si falla, consulta el paso y la evidencia: un error de permisos, descarga de imagen o programación del cliente no demuestra por sí solo un fallo HTTP de la app.

activate y restore también usan ese cliente temporal con la misma imagen ECR que la aplicación. No añaden herramientas a la imagen ni requieren otra imagen pública. El cliente tiene etiquetas distintas para no recibir tráfico de la aplicación.

Para este escenario usa restore del workflow Run SRE lab 04, no baseline. baseline sigue siendo la recuperación de lab-01 y lab-02. Los workflows impiden mezclar ejercicios marcados como activos.

## Grafana y evidencia

```bash
aws eks update-kubeconfig \
  --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default
kubectl -n monitoring port-forward service/kube-prometheus-stack-grafana 3000:80
```

Abre http://localhost:3000/d/sre-simple-test. Las credenciales y los detalles de acceso están en lab-03-start.md. Observa la última media hora con actualización cada 30 segundos. Relaciona cada gráfica con una pregunta; no supongas que todas las fallas deben producir un cambio en todos los paneles. El dashboard actual no mide HTTP continuamente.

Guarda hora, alcance, estado actual, eventos, consultas y resultados de la prueba de cliente. Construye la hipótesis antes de proponer cambios. No abras lab04.py para evitar adelantarte la respuesta.

## Cancelación y recuperación

La configuración original se guarda antes de activar el fallo. Si cancelas activate o restore, guarda el enlace y utiliza restore del mismo workflow para recuperar. No vuelvas a activar sobre un registro existente.

restore conserva el registro hasta comprobar la recuperación. Si falta ese registro o un recurso fue reemplazado, se detiene para evitar modificar recursos ajenos. Si cancelaste antes de guardar el registro, puede no haber incidente aplicado: revisa el último paso y el estado actual.

Los Pods de prueba tienen un tiempo máximo de ejecución. La siguiente operación limpia los clientes de prueba que hayan quedado de una cancelación. No se borran Pods de la aplicación ni se cambian nodos.

## Cierre y estado de validación

Puedes ejecutar Terraform Decommission sin restaurar primero. Guarda capturas y notas antes: el historial de Prometheus y los recursos del ejercicio se eliminan con el entorno. Confirma Decommission en verde.

La preparación se valida localmente. La comprobación real del escenario se ejecutará en tu clúster cuando actives el workflow. El workflow usa el rol existente de Terraform; tu usuario conserva su rol de diagnóstico.
