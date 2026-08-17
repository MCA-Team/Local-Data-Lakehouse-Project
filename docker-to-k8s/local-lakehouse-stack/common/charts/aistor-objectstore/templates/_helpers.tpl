{{/* vim: set filetype=mustache: */}}
{{/*
Renders a value that contains template.
Usage:
{{ include "aistor.render" ( dict "value" .Values.path.to.the.Value "context" $) }}
*/}}
{{- define "aistor.render" -}}
  {{- if typeIs "string" .value }}
    {{- tpl .value .context }}
  {{- else }}
    {{- tpl (.value | toYaml) .context }}
  {{- end }}
{{- end -}}


{{- define "aistor.configSecretName" -}}
{{- $secretConfigName := dig "secrets" "name" "" (. | merge (dict)) | default "" }}
{{- $objectStoreConfigSecret := dig "objectStore" "configuration" "name" "" (. | merge (dict)) | default "" }}
{{- if not $objectStoreConfigSecret }}
{{- $objectStoreConfigSecret = $secretConfigName }}
{{- end }}
{{- if not $secretConfigName }}
{{- $secretConfigName = $objectStoreConfigSecret }}
{{- end }}
{{- if and $secretConfigName $objectStoreConfigSecret }}
{{- if not (eq $secretConfigName $objectStoreConfigSecret) }}
{{- fail "Configuration secret mismatch in .secrets.name and .objectStore.configuration.name" -}}
{{- end }}
{{- end }}
{{- $secretConfigName }}
{{- end }}
