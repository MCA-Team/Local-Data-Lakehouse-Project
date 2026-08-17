{{/* 
    aistor.namespace returns the namespace for AIStor resources.
*/}}
{{- define "aistor.namespace" -}}
{{ $.Values.namespaceOverride | default $.Release.Namespace| trunc 63 | trimSuffix "-" | quote }}
{{- end -}}

{{/* 
    aistor.resolveImage resolves the given name into a fully qualified image name.
    - name: the name of the image in $.images
    - root: the root object
    - val: the value of the image in the current object
*/}}
{{- define "aistor.resolveImage" -}}
{{- if .val.image -}}
  {{- .val.image -}}
{{- else -}}
  {{- $emptyObj := ("{}" | fromJson) -}}
  {{- $images := .root.images | default $emptyObj -}}
  {{- $imageDef := index $images .name -}}
  {{- if not $imageDef -}}
    {{ fail (printf "Image '%s' not found in images definition" .name) }}
  {{- else if kindIs "string" $imageDef }}
    {{- $imageDef -}}
  {{- else if kindIs "map" $imageDef }}
    {{- if (not $imageDef.repository) }}
      {{ fail (printf "Image definition for '%s' must have a 'repository' field" .name) }}
    {{- end -}}
    {{- $repo := index (.root.repositories | default $emptyObj) $imageDef.repository -}}
    {{- if (not $repo) -}}
      {{ fail (printf "Unknown repository '%s' for image '%s'" $imageDef.repository .name) }}
    {{- end -}}

    {{- if (not $imageDef.image) }}
      {{ fail (printf "Image definition for '%s' must have an 'image' field" .name) }}
    {{- end -}}
    {{- $defaultImage := printf "%s%s" ($repo.pathPrefix | default "") $imageDef.image -}}
    {{- if $repo.hostname }}
      {{- $defaultImage = printf "%s/%s" $repo.hostname $defaultImage -}}
    {{- end }}
    {{- $defaultImage -}}
  {{- end }}
{{- end -}}
{{- end -}}

{{/* 
    aistor.resolveImagePullPolicy resolves the given name into a pull policy.
    - name: the name of the image in $.images
    - root: the root object
    - val: the value of the pull policy in the current object
*/}}
{{- define "aistor.resolveImagePullPolicy" -}}
{{- $emptyObj := ("{}" | fromJson) -}}
{{- $images := .root.images | default $emptyObj -}}
{{- $imageDef := index $images .name -}}
{{- if kindIs "map" $imageDef }}
{{- $repositoryName := $imageDef.repository | default "" -}}
{{- $repo := index .root.repositories $repositoryName | default $emptyObj -}}
{{- .val.imagePullPolicy | default $repo.imagePullPolicy | default "" -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}

{{/* 
    aistor.resolveImagePullSecrets resolves the given name into a pull secrets.
    - name: the name of the image in $.images
    - root: the root object
*/}}
{{- define "aistor.resolveImagePullSecrets" -}}
{{- $emptyObj := ("{}" | fromJson) -}}
{{- $emptyArray := ("[]" | fromJsonArray) -}}
{{- $images := .root.images | default $emptyObj -}}
{{- $imageDef := index $images .name -}}
{{- if kindIs "map" $imageDef }}
{{- $repositoryName := $imageDef.repository | default "" -}}
{{- $repo := index .root.repositories $repositoryName | default $emptyObj -}}
{{- $repo.imagePullSecrets | default $emptyArray | toJson -}}
{{- else -}}
{{- $emptyArray | toJson -}}
{{- end -}}
{{- end -}}

{{/* 
    aistor.resolveEnv resolves the given name into the environment.
    - name: the name of the image in $.images
    - root: the root object
*/}}
{{- define "aistor.resolveEnv" -}}
{{- $emptyObj := ("{}" | fromJson) -}}
{{- $emptyArray := ("[]" | fromJsonArray) -}}
{{- $images := .root.images | default $emptyObj -}}
{{- $imageDef := index $images .name | default $emptyObj -}}
{{- if kindIs "map" $imageDef }}
{{- $imageDef.env | default $emptyArray | toJson -}}
{{- else -}}
{{- $emptyArray | toJson -}}
{{- end -}}
{{- end -}}

{{/*
    aistor.isOpenShift returns whether the current cluster is OpenShift.
*/}}
{{- define "aistor.isOpenShift" -}}
{{- if ($.Values.global.forceOpenShift | default (.Capabilities.APIVersions.Has "security.openshift.io/v1/SecurityContextConstraints")) -}}
{{- true -}}
{{- end -}}
{{- end -}}


{{/*
    aistor.webhookUsesCustomCert returns "true" when the object-store webhook is
    configured to serve a custom TLS certificate, detected by a non-empty
    WEBHOOK_CUSTOM_TLS_SECRET_NAME in webhook.extraEnv. The OpenShift service-ca
    wiring (inject-cabundle annotation, serving cert and its read-only mount) is
    skipped in that case so the custom certificate path owns the serving cert
    and CA bundle on OpenShift too.
*/}}
{{- define "aistor.webhookUsesCustomCert" -}}
{{- $emptyObj := "{}" | fromJson -}}
{{- $operators := .Values.operators | default $emptyObj -}}
{{- $objectStore := index $operators "object-store" | default $emptyObj -}}
{{- $webhook := index $objectStore "webhook" | default $emptyObj -}}
{{- range ($webhook.extraEnv | default list) -}}
{{- if and (eq .name "WEBHOOK_CUSTOM_TLS_SECRET_NAME") (ne (toString .value) "") -}}
{{- true -}}
{{- end -}}
{{- end -}}
{{- end -}}


{{/*
    aistor.operatorEnabled returns whether the operator is enabled.
*/}}
{{- define "aistor.operatorEnabled" -}}
{{- $emptyObj := "{}" | fromJson -}}
{{- $operators := .root.operators | default $emptyObj -}}
{{- $opValue := index $operators .operator | default $emptyObj }}
{{- if not $opValue.disabled }}
{{- true -}}
{{- end -}}
{{- end -}}

{{/*
    aistor.webhookEnabled returns whether the object-store webhook is enabled.
    Webhook is enabled when:
    - object-store operator is not disabled AND
    - webhook is not explicitly set to false (boolean) AND
    - webhook.enabled is not false
*/}}
{{- define "aistor.webhookEnabled" -}}
{{- $emptyObj := "{}" | fromJson -}}
{{- $operators := .Values.operators | default $emptyObj -}}
{{- $objectStore := index $operators "object-store" | default $emptyObj -}}
{{- $webhookRaw := index $objectStore "webhook" -}}
{{- $webhook := $webhookRaw | default $emptyObj -}}
{{- $webhookExplicitlyFalse := and (kindIs "bool" $webhookRaw) (not $webhookRaw) -}}
{{- if and (not $objectStore.disabled) (not (or $webhookExplicitlyFalse (eq $webhook.enabled false))) -}}
{{- true -}}
{{- end -}}
{{- end -}}

{{/*
    aistor.operators returns the default information for all operators
*/}}
{{- define "aistor.operators" -}}
adminjob:
  images: ["mc"]
aihub:
  images: ["aihub"]
object-store:
  images: ["minwall","kes","kes-sidecar","minio","minio-sidecar"]
prompt:
  images: ["prompt"]
warp:
  images: ["warp"]
{{- end -}}

{{/*
    aistor.tokenValidation returns the token validation mode for the object-store operator.
*/}}
{{- define "aistor.tokenValidation" -}}
{{- dig "operators" "object-store" "tokenValidation" "TokenReview" (.Values | merge (dict)) -}}
{{- end -}}

{{/*
    aistor.watchedNamespaces returns the list of watched namespaces for an operator.
    Per-operator value takes precedence over global.operator.watchedNamespaces.
    Returns an empty list when neither is set (cluster-wide mode).
    - operator: the operator name
    - root: the root values object
*/}}
{{- define "aistor.watchedNamespaces" -}}
{{- $emptyObj := "{}" | fromJson -}}
{{- $emptyArray := "[]" | fromJsonArray -}}
{{- $operators := .root.operators | default $emptyObj -}}
{{- $opValue := index $operators .operator | default $emptyObj -}}
{{- $globalOp := ((.root.global | default $emptyObj).operator) | default $emptyObj -}}
{{- if hasKey $opValue "watchedNamespaces" -}}
{{- $opValue.watchedNamespaces | toJson -}}
{{- else if hasKey $globalOp "watchedNamespaces" -}}
{{- $globalOp.watchedNamespaces | toJson -}}
{{- else -}}
{{- $emptyArray | toJson -}}
{{- end -}}
{{- end -}}
