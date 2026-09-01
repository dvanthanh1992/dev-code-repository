{{- define "msp-demo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "msp-demo.fullname" -}}
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

{{- define "msp-demo.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "msp-demo.labels" -}}
helm.sh/chart: {{ include "msp-demo.chart" . }}
{{ include "msp-demo.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "msp-demo.selectorLabels" -}}
app.kubernetes.io/name: {{ include "msp-demo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "msp-demo.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "msp-demo.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "msp-demo.strategy" -}}
{{- $strategy := (.Values.strategy | default "canary" | lower | replace "-" "" | replace "_" "") -}}
{{- if eq $strategy "canary" -}}
canary
{{- else if eq $strategy "bluegreen" -}}
blueGreen
{{- else -}}
{{- fail (printf "strategy must be canary or blueGreen, got %q" .Values.strategy) -}}
{{- end -}}
{{- end }}

{{- define "msp-demo.previewServiceName" -}}
{{- printf "%s-preview" (include "msp-demo.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "msp-demo.previewUrl" -}}
{{- $strategy := include "msp-demo.strategy" . -}}
{{- if and (eq $strategy "blueGreen") .Values.previewIngress.enabled .Values.previewIngress.host -}}
{{- if .Values.previewIngress.tls.enabled -}}https{{- else -}}http{{- end -}}://{{ .Values.previewIngress.host }}/api/ping
{{- end -}}
{{- end }}

{{- define "msp-demo.redisFullname" -}}
{{- printf "%s-redis" (include "msp-demo.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "msp-demo.redisHost" -}}
{{- if .Values.redis.enabled }}
{{- include "msp-demo.redisFullname" . }}
{{- else }}
{{- required "redis.host is required when redis.enabled=false" .Values.redis.host }}
{{- end }}
{{- end }}

{{- define "msp-demo.redisSecretName" -}}
{{- required "redis.auth.existingSecret is required when Redis auth is enabled" .Values.redis.auth.existingSecret }}
{{- end }}
