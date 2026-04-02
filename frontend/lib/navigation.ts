import type { UserRole } from './api';

export type NavIcon = 'book' | 'none';

export interface NavItem {
  href: string;
  label: string;
  description: string;
  roles?: UserRole[];
  icon?: NavIcon;
  section?: 'principal' | 'administracao';
}

export const APP_NAVIGATION: NavItem[] = [
  {
    href: '/dashboard',
    label: 'Dashboard',
    description: 'Operational metrics and status overview',
    roles: ['super_admin', 'librarian', 'assistant', 'member'],
    icon: 'none',
    section: 'principal'
  },
  {
    href: '/catalog',
    label: 'Catalog',
    description: 'Search and curate bibliographic records',
    roles: ['super_admin', 'librarian', 'assistant'],
    icon: 'none',
    section: 'principal'
  },
  {
    href: '/catalog/advanced',
    label: 'Advanced Catalog',
    description: 'Create MARC21-ready bibliographic records',
    roles: ['super_admin', 'librarian'],
    icon: 'none',
    section: 'principal'
  },
  {
    href: '/loans',
    label: 'Empréstimos',
    description: 'Registrar novos empréstimos e monitorar ativos',
    roles: ['super_admin', 'librarian', 'assistant'],
    icon: 'none',
    section: 'principal'
  },
  {
    href: '/returns',
    label: 'Devoluções',
    description: 'Processar devoluções de empréstimos ativos',
    roles: ['super_admin', 'librarian', 'assistant'],
    icon: 'none',
    section: 'principal'
  },
  {
    href: '/reservations',
    label: 'Reservas',
    description: 'Acompanhar fila por livro e status',
    roles: ['super_admin', 'librarian', 'assistant', 'member'],
    icon: 'none',
    section: 'principal'
  },
  {
    href: '/users',
    label: 'Users',
    description: 'Manage tenant users and access control',
    roles: ['super_admin', 'librarian'],
    icon: 'none',
    section: 'administracao'
  },
  {
    href: '/settings/libraries',
    label: 'Bibliotecas',
    description: 'Manage tenant libraries and multi-unit setup',
    roles: ['super_admin'],
    icon: 'book',
    section: 'administracao'
  },
  {
    href: '/fines',
    label: 'Fines',
    description: 'Review and settle overdue fines',
    roles: ['super_admin', 'librarian', 'assistant'],
    icon: 'none',
    section: 'principal'
  },
  {
    href: '/reports',
    label: 'Reports',
    description: 'Track KPIs and compliance reporting',
    roles: ['super_admin', 'librarian'],
    icon: 'none',
    section: 'principal'
  }
];

export function navigationForRole(role: UserRole): NavItem[] {
  return APP_NAVIGATION.filter((item) => !item.roles || item.roles.includes(role));
}
