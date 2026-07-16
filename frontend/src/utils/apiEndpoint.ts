import type { ApiEndpoint } from '../types/api'

export function endpointKeyFor(endpoint: ApiEndpoint) {
  return endpoint.endpoint_key
    ?? ['legacy-endpoint', endpoint.method, endpoint.path, endpoint.handler, endpoint.file_path, endpoint.start_line].join(':')
}
