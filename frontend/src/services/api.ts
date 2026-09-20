import { frappeRequest } from "frappe-ui"

export const api = {
  get(method: string, params?: Record<string, any>) {
    return frappeRequest({ method: "GET", url: `/api/method/${method}`, params })
  },
  post(method: string, params?: Record<string, any>) {
    return frappeRequest({ method: "POST", url: `/api/method/${method}`, params })
  }
}
