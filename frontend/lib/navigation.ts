import type { UserRole } from './api';

export interface NavItem {
  href: string;
  label: string;
  description: string;
  roles: UserRole[];
}

export const APP_NAVIGATION: NavItem[] = [
  {
    href: '/dashboard',
    label: 'Dashboard',
    description: 'Operational metrics and status overview',
    roles: ['super_admin', 'librarian', 'assistant', 'member']
  },
  {
    href: '/catalog',
    label: 'Catalog',
    description: 'Search and curate bibliographic records',
    roles: ['super_admin', 'librarian', 'assistant']
  },
  {
    href: '/loans',
    label: 'Loans',
    description: 'Manage circulation and due dates',
    roles: ['super_admin', 'librarian', 'assistant']
  },
  {
    href: '/users',
    label: 'Users',
    description: 'Manage tenant users and access control',
    roles: ['super_admin', 'librarian']
  },
  {
    href: '/reports',
    label: 'Reports',
    description: 'Track KPIs and compliance reporting',
    roles: ['super_admin', 'librarian']
  }
];

export function navigationForRole(role: UserRole): NavItem[] {
  return APP_NAVIGATION.filter((item) => item.roles.includes(role));
}
