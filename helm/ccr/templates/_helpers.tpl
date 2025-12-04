{{/*
Expand the name of the chart.
*/}}
{{- define "ccr.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ccr.fullname" -}}
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
Create chart name and version as used by the chart label.
*/}}
{{- define "ccr.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ccr.labels" -}}
helm.sh/chart: {{ include "ccr.chart" . }}
{{ include "ccr.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ccr.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ccr.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Flask selector labels
*/}}
{{- define "ccr.flask.selectorLabels" -}}
{{ include "ccr.selectorLabels" . }}
app.kubernetes.io/component: flask
{{- end }}

{{/*
MongoDB selector labels
*/}}
{{- define "ccr.mongodb.selectorLabels" -}}
{{ include "ccr.selectorLabels" . }}
app.kubernetes.io/component: mongodb
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ccr.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ccr.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Flask image name
*/}}
{{- define "ccr.flask.image" -}}
{{- $registry := .Values.image.registry }}
{{- $repository := .Values.image.repository }}
{{- $tag := .Values.image.tag | default .Chart.AppVersion }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- end }}

{{/*
MongoDB image name
*/}}
{{- define "ccr.mongodb.image" -}}
{{- $registry := .Values.mongodb.image.registry }}
{{- $repository := .Values.mongodb.image.repository }}
{{- $tag := .Values.mongodb.image.tag }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- end }}

{{/*
Flask service name
*/}}
{{- define "ccr.flask.serviceName" -}}
{{- printf "%s-flask" (include "ccr.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
MongoDB service name
*/}}
{{- define "ccr.mongodb.serviceName" -}}
{{- printf "%s-mongodb" (include "ccr.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
MongoDB headless service name
*/}}
{{- define "ccr.mongodb.headlessServiceName" -}}
{{- printf "%s-mongodb-headless" (include "ccr.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
MongoDB StatefulSet name
*/}}
{{- define "ccr.mongodb.statefulsetName" -}}
{{- printf "%s-mongodb" (include "ccr.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
ConfigMap name
*/}}
{{- define "ccr.configMapName" -}}
{{- printf "%s-config" (include "ccr.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Secret name
*/}}
{{- define "ccr.secretName" -}}
{{- printf "%s-secrets" (include "ccr.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Backup PVC name
*/}}
{{- define "ccr.backup.pvcName" -}}
{{- printf "%s-backup" (include "ccr.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
MongoDB PVC name (used by StatefulSet)
*/}}
{{- define "ccr.mongodb.pvcName" -}}
{{- printf "mongodb-data" }}
{{- end }}

{{/*
Return the appropriate apiVersion for HPA
*/}}
{{- define "ccr.hpa.apiVersion" -}}
{{- if .Capabilities.APIVersions.Has "autoscaling/v2" }}
{{- print "autoscaling/v2" }}
{{- else }}
{{- print "autoscaling/v2beta2" }}
{{- end }}
{{- end }}

{{/*
Return the appropriate apiVersion for Ingress
*/}}
{{- define "ccr.ingress.apiVersion" -}}
{{- if .Capabilities.APIVersions.Has "networking.k8s.io/v1" }}
{{- print "networking.k8s.io/v1" }}
{{- else if .Capabilities.APIVersions.Has "networking.k8s.io/v1beta1" }}
{{- print "networking.k8s.io/v1beta1" }}
{{- else }}
{{- print "extensions/v1beta1" }}
{{- end }}
{{- end }}

{{/*
Environment name from global or release name
*/}}
{{- define "ccr.environment" -}}
{{- .Values.global.environment | default "dev" }}
{{- end }}

{{/*
Return true if external secrets should be used
*/}}
{{- define "ccr.useExternalSecrets" -}}
{{- if .Values.externalSecrets.enabled }}
{{- print "true" }}
{{- else }}
{{- print "false" }}
{{- end }}
{{- end }}

{{/*
Create a default set of common pod labels
*/}}
{{- define "ccr.podLabels" -}}
{{- range $key, $value := .Values.podLabels }}
{{ $key }}: {{ $value | quote }}
{{- end }}
environment: {{ include "ccr.environment" . }}
{{- end }}

{{/*
Validate required values
*/}}
{{- define "ccr.validateValues" -}}
{{- if not .Values.image.tag }}
  {{- if eq (include "ccr.environment" .) "prd" }}
    {{- fail "image.tag is required for production deployments" }}
  {{- end }}
{{- end }}
{{- if and .Values.externalSecrets.enabled (not .Values.externalSecrets.backendType) }}
  {{- fail "externalSecrets.backendType is required when externalSecrets.enabled is true" }}
{{- end }}
{{- end }}
