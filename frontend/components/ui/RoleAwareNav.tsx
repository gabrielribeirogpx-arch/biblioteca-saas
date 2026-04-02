'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import type { UserRole } from '../../lib/api';
import { navigationForRole } from '../../lib/navigation';

interface RoleAwareNavProps {
  role: UserRole;
}

function BookIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 text-brand-700">
      <path
        d="M5 4.5A2.5 2.5 0 0 1 7.5 2H20v18H7.5A2.5 2.5 0 0 0 5 22V4.5Zm0 17.25c.42-.47.98-.75 1.62-.75H18V3.5H7.5A1 1 0 0 0 6.5 4.5V18c.31-.16.65-.25 1-.25h9v1.5h-9A1.5 1.5 0 0 0 6 20.75Zm-2-16h1.5v16.5H3v-16.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function RoleAwareNav({ role }: RoleAwareNavProps) {
  const pathname = usePathname();
  const items = navigationForRole(role);
  const principalItems = items.filter((item) => item.section !== 'administracao');
  const adminItems = items.filter((item) => item.section === 'administracao');

  const renderItem = (item: (typeof items)[number]) => {
    const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

    return (
      <Link
        className={`block rounded-lg px-3 py-2 text-sm transition ${
          isActive ? 'bg-brand-50 text-brand-900 ring-1 ring-brand-200' : 'text-slate-700 hover:bg-brand-50 hover:text-brand-900'
        }`}
        href={item.href}
        key={item.href}
      >
        <p className="flex items-center gap-2 font-semibold">
          {item.icon === 'book' ? <BookIcon /> : null}
          <span>{item.label}</span>
        </p>
        <p className={`text-xs ${isActive ? 'text-brand-700' : 'text-slate-500'}`}>{item.description}</p>
      </Link>
    );
  };

  return (
    <nav className="space-y-4">
      <div className="space-y-1">{principalItems.map((item) => renderItem(item))}</div>

      {adminItems.length > 0 ? (
        <div className="border-t border-slate-200 pt-4">
          <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Administração</p>
          <div className="space-y-1">{adminItems.map((item) => renderItem(item))}</div>
        </div>
      ) : null}
    </nav>
  );
}
