import { cookies } from 'next/headers';

import type { UserRole } from './api';

const FALLBACK_ROLE: UserRole = 'member';

export function getCurrentRole(): UserRole {
  const role = cookies().get('library_role')?.value as UserRole | undefined;

  if (role === 'super_admin' || role === 'librarian' || role === 'assistant' || role === 'member') {
    return role;
  }

  return FALLBACK_ROLE;
}
