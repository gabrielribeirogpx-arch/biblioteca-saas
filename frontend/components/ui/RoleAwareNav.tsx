import Link from 'next/link';

import type { UserRole } from '../../lib/api';
import { navigationForRole } from '../../lib/navigation';

interface RoleAwareNavProps {
  role: UserRole;
}

export function RoleAwareNav({ role }: RoleAwareNavProps) {
  const items = navigationForRole(role);

  return (
    <nav className="space-y-1">
      {items.map((item) => (
        <Link
          className="block rounded-lg px-3 py-2 text-sm text-slate-700 transition hover:bg-brand-50 hover:text-brand-900"
          href={item.href}
          key={item.href}
        >
          <p className="font-semibold">{item.label}</p>
          <p className="text-xs text-slate-500">{item.description}</p>
        </Link>
      ))}
    </nav>
  );
}
