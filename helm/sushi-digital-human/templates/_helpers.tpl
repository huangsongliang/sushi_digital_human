{{/*
Expand the name of the chart.
*/}}
{{- define "sushi-digital-human.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "sushi-digital-human.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "sushi-digital-human.labels" -}}
helm.sh/chart: {{ include "sushi-digital-human.name" . }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "sushi-digital-human.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
API selector labels.
*/}}
{{- define "sushi-digital-human.apiSelectorLabels" -}}
app.kubernetes.io/name: {{ include "sushi-digital-human.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Nginx selector labels.
*/}}
{{- define "sushi-digital-human.nginxSelectorLabels" -}}
app.kubernetes.io/name: {{ include "sushi-digital-human.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: nginx
{{- end }}

{{/*
Redis selector labels.
*/}}
{{- define "sushi-digital-human.redisSelectorLabels" -}}
app.kubernetes.io/name: {{ include "sushi-digital-human.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: redis
{{- end }}
