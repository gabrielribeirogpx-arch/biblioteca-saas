import type { UserRole } from './api';

export type NavIcon = 'book' | 'none';

export interface NavItem {
  href: string;
  label: string;
  description: string;
  roles: UserRole[];
  icon?: NavIcon;
}

export const APP_NAVIGATION: NavItem[] = [
  {
    href: '/dashboard',
    label: 'Dashboard',
    description: 'Operational metrics and status overview',
    roles: ['super_admin', 'librarian', 'assistant', 'member'],
    icon: 'none'
  },
  {
    href: '/catalog',
    label: 'Catalog',
    description: 'Search and curate bibliographic records',
    roles: ['super_admin', 'librarian', 'assistant'],
    icon: 'none'
  },
  {
    href: '/catalog/advanced',
    label: 'Advanced Catalog',
    description: 'Create MARC21-ready bibliographic records',
    roles: ['super_admin', 'librarian'],
    icon: 'none'
  },
  {
    href: '/loans',
    label: 'Loans',
    description: 'Manage circulation and due dates',
    roles: ['super_admin', 'librarian', 'assistant'],
    icon: 'none'
  },
  {
    href: '/users',
    label: 'Users',
    description: 'Manage tenant users and access control',
    roles: ['super_admin', 'librarian'],
    icon: 'none'
  },
  {
    href: '/settings/libraries',
    label: 'Bibliotecas',
    description: 'Manage tenant libraries and multi-unit setup',
    roles: ['super_admin'],
    icon: 'book'
  },
  {
    href: '/reservations',
    label: 'Reservations',
    description: 'Track book reservations and queue status',
    roles: ['super_admin', 'librarian', 'assistant', 'member'],
    icon: 'none'
  },
  {
    href: '/fines',
    label: 'Fines',
    description: 'Review and settle overdue fines',
    roles: ['super_admin', 'librarian', 'assistant'],
    icon: 'none'
  },
  {
    href: '/reports',
    label: 'Reports',
    description: 'Track KPIs and compliance reporting',
    roles: ['super_admin', 'librarian'],
    icon: 'none'
  }
];

export function navigationForRole(role: UserRole): NavItem[] {
  return APP_NAVIGATION.filter((item) => item.roles.includes(role));
}
