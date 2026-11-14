// English description of any error raised by the data source. The backend `detail` text is not shown
// (it is written for developers); the stable `code` selects the message, and the coverage limits or
// the invalid field paths (technical identifiers) are added when present.

import { en } from '../i18n/en.ts'
import { ApiError, NetworkError } from './dataSource.ts'

export interface ErrorDescription {
  code: string | null
  message: string
  details: string[]
}

export function describeError(error: unknown): ErrorDescription {
  if (error instanceof NetworkError) {
    return { code: null, message: en.errors.network, details: [] }
  }
  if (error instanceof ApiError && error.problem) {
    const problem = error.problem
    const details: string[] = []
    if (problem.coverage_start_utc && problem.coverage_end_utc) {
      details.push(
        en.errors.coverageLimits(
          problem.coverage_start_utc,
          problem.coverage_end_utc,
        ),
      )
    }
    if (problem.field_errors && problem.field_errors.length > 0) {
      const paths = problem.field_errors
        .map((field) => field.loc.filter((part) => part !== 'body').join('.'))
        .filter((path) => path.length > 0)
      if (paths.length > 0) details.push(en.errors.fields(paths.join(', ')))
    }
    return {
      code: problem.code,
      message: en.errors.codes[problem.code] ?? en.errors.unexpected,
      details,
    }
  }
  if (error instanceof ApiError && error.status === 0) {
    return { code: null, message: en.errors.network, details: [] }
  }
  return { code: null, message: en.errors.unexpected, details: [] }
}
