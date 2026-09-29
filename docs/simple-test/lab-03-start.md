# Laboratorio 03 y observabilidad

## Preparación y alcance

Este ejercicio practica un problema de programación de Pods relacionado con un nodo. Es una simulación controlada: no reproduce una caída real de kubelet ni presión física de memoria. La causa concreta se investiga en Kubernetes, sin abrir el script del ejercicio previamente.

Los componentes de observabilidad ya se instalan con Provision. Configure SRE observability añade el dashboard y las reglas del laboratorio; no crea otro Prometheus ni otro Grafana. Los workflows son manuales y no se ejecutan al hacer push.

## Orden para empezar

1. Ejecuta Terraform Provision en main. Espera resultado verde. Incluye el permiso para abrir túneles a las interfaces de monitoring con tu usuario.
2. Ejecuta Deploy simple-test en main. Espera verde, incluido HTTP. Si la app ya existe por una ejecución cancelada, valida con Update simple-test / baseline antes de continuar.
3. Ejecuta Configure SRE observability en main. Espera verde. Verifica métricas reales, seis reglas sanas y nueve paneles importados en Grafana.
4. Abre Grafana y observa unos minutos de comportamiento sano. Guarda hora y captura como referencia.
5. Ejecuta Run SRE lab 03 en main, operation activate. Este workflow NO es Update simple-test. No existe lab-03 en el selector de Update simple-test.
6. Un resultado verde en activate significa que el escenario y su síntoma fueron comprobados, NO que la aplicación completó un rollout sano. Si falla, guarda el enlace; no supongas que el ejercicio se activó completamente.
7. Pide a Theo el enunciado del lab-03, sin revelar la causa. Investiga estado actual, eventos y evolución temporal en Grafana.

## Opciones y recuperación

| Workflow y opción | Propósito |
|---|---|
| Configure SRE observability | Crear o actualizar el dashboard y las reglas, y verificar su carga |
| Update simple-test / baseline | Recuperar los cambios de lab-01 o lab-02 |
| Run SRE lab 03 / activate | Activar el tercer ejercicio sobre la app sana |
| Run SRE lab 03 / restore | Recuperar el nodo y la plantilla original de la app, validar rollout y HTTP |
| Terraform Decommission | Cerrar el ambiente completo, incluso si el ejercicio quedó activo |

Para lab-03 usa restore, no baseline. Update simple-test bloquea cambios mientras el tercer ejercicio está marcado activo. Guarda evidencia antes de restaurar. La recuperación conserva datos hasta que rollout y HTTP pasan; si se interrumpe, vuelve a ejecutar restore. Si ya no hay registro, el workflow se detiene sin modificar nada. No combina ejercicios: primero recupera el anterior.

Los workflows nuevos usan el rol existente de Terraform, que administra el clúster. El rol de despliegue de la app conserva sus permisos actuales. No se conceden permisos de modificación de nodos a tu usuario de diagnóstico. El único permiso humano adicional es abrir port-forward en monitoring.

## Acceso local a Grafana y Prometheus

Actualiza kubeconfig después de cada Provision:

```bash
aws eks update-kubeconfig \
  --name eks-learning-lab-lab-eks \
  --region us-east-1 --profile default
```

En una terminal, deja este túnel abierto:

```bash
kubectl -n monitoring port-forward service/kube-prometheus-stack-grafana 3000:80
```

Abre http://localhost:3000. Consulta las credenciales localmente; no las pegues en chats, capturas ni reportes:

```bash
kubectl -n monitoring get secret kube-prometheus-stack-grafana \
  -o jsonpath='{.data.admin-user}' | base64 --decode
kubectl -n monitoring get secret kube-prometheus-stack-grafana \
  -o jsonpath='{.data.admin-password}' | base64 --decode
```

Busca el dashboard SRE Lab — simple-test and nodes. Selecciona el datasource Prometheus que consulta la instancia del stack. Usa la última hora y actualización cada 30 segundos. El dashboard separa consumo, requests y limits; no asumas que una línea baja de consumo significa que un Pod puede ser programado.

En otra terminal puedes abrir Prometheus:

```bash
kubectl -n monitoring port-forward service/kube-prometheus-stack-prometheus 9090:9090
```

Abre http://localhost:9090 y consulta Alerts. Las reglas esperan entre uno y dos minutos de condición sostenida antes de dispararse, además del intervalo de evaluación. No hay correo ni Slack configurados. No recibir una notificación externa no demuestra que no haya alertas.

## Qué observamos

El dashboard contiene réplicas deseadas, disponibles y actualizadas; fases de Pods; reinicios; consumo, requests y limits de CPU/memoria; Ready de nodos; disponibilidad para programar Pods; presión del nodo y CPU asignable. Métricas de contenedores que nunca arrancaron pueden estar ausentes, mientras sus requests y estado sí aparecen.

No añadimos métricas HTTP internas de Nginx, latencia de peticiones ni centralización de logs. Los workflows comprueban HTTP por túnel; los logs se consultan con kubectl. Este dashboard no convierte la prueba por túnel en una prueba de toda la ruta Service.

## Cierre

Guarda capturas, consultas y horas antes de Decommission. Prometheus y Grafana usan almacenamiento efímero: se pierde el historial al destruir el entorno. El dashboard y las alertas se recrean ejecutando Configure SRE observability después del siguiente Provision y Deploy. No hace falta restore antes de Decommission.

## Estado de validación

Código y manifiestos se verifican localmente. Las APIs reales de EKS, Prometheus y Grafana se validarán en los workflows de mañana. No se ejecutó el ejercicio contra un clúster durante su preparación.
