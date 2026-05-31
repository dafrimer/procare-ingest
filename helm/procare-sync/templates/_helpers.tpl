{{/*
Expand the name of the chart.
*/}}
{{- define "procare-sync.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "procare-sync.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart label.
*/}}
{{- define "procare-sync.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "procare-sync.labels" -}}
helm.sh/chart: {{ include "procare-sync.chart" . }}
{{ include "procare-sync.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "procare-sync.selectorLabels" -}}
app.kubernetes.io/name: {{ include "procare-sync.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
DB host: use bundled mysql if db.host is empty and mysql.enabled.
*/}}
{{- define "procare-sync.dbHost" -}}
{{- if .Values.db.host -}}
{{ .Values.db.host }}
{{- else if .Values.mysql.enabled -}}
{{ include "procare-sync.fullname" . }}-mysql
{{- else -}}
localhost
{{- end }}
{{- end }}
