'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { AppShell } from '../../components/ui/AppShell';
import { DataTable } from '../../components/ui/DataTable';
import { useAuth } from '../../hooks/useAuth';
import {
  ApiError,
  createUser,
  deleteUser,
  getUsers,
  getUsersMetadata,
  updateUser,
  type User,
  type UserCreateInput,
  type UserMetadata,
  type UserRole
} from '../../lib/api';
import { hasPermission } from '../../lib/permissions';

interface UserRow {
  [key: string]: string | number | null | undefined;
  id: number;
  full_name: string;
  email: string;
  role: string;
  libraries: string;
  permissions: string;
  status: string;
}

type ModalMode = 'create' | 'edit';

const roleOptions: UserRole[] = ['super_admin', 'librarian', 'assistant', 'member'];

export default function UsersPage() {
  const { role, loading, permissions } = useAuth();
  const [rows, setRows] = useState<UserRow[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [metadata, setMetadata] = useState<UserMetadata>({ roles: [], libraries: [] });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalMode, setModalMode] = useState<ModalMode>('create');
  const [editingUserId, setEditingUserId] = useState<number | null>(null);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [userRole, setUserRole] = useState<UserRole>('member');
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);
  const [selectedLibraryIds, setSelectedLibraryIds] = useState<number[]>([]);
  const [isActive, setIsActive] = useState(true);

  async function loadData() {
    if (!hasPermission('users.read', permissions)) {
      setRows([]);
      return;
    }

    try {
      const [usersResponse, metadataResponse] = await Promise.all([getUsers(), getUsersMetadata()]);
      const loadedUsers = usersResponse.items ?? [];
      setUsers(loadedUsers);
      setMetadata(metadataResponse);
      setRows(
        loadedUsers.map((user) => ({
          id: user.id,
          full_name: user.full_name,
          email: user.email,
          role: user.role,
          libraries: user.libraries.map((library) => library.name).join(', '),
          permissions: user.permissions.join(', '),
          status: user.is_active ? 'Ativo' : 'Inativo'
        }))
      );
    } catch {
      setError('Erro ao carregar usuários.');
      setRows([]);
    }
  }

  useEffect(() => {
    if (loading) {
      return;
    }
    void loadData();
  }, [loading, permissions]);

  const canSubmit = useMemo(() => {
    const baseValid = fullName.trim().length > 1 && email.trim().length > 3 && selectedLibraryIds.length > 0;
    if (modalMode === 'create') {
      return baseValid && password.length >= 6;
    }
    return baseValid;
  }, [email, fullName, modalMode, password.length, selectedLibraryIds.length]);

  function resetModal() {
    setFullName('');
    setEmail('');
    setPassword('');
    setUserRole('member');
    setSelectedRoleIds([]);
    setSelectedLibraryIds([]);
    setIsActive(true);
    setEditingUserId(null);
    setModalMode('create');
  }

  function openCreateModal() {
    resetModal();
    setError('');
    setSuccess('');
    setIsModalOpen(true);
  }

  function openEditModal(user: User) {
    setModalMode('edit');
    setEditingUserId(user.id);
    setFullName(user.full_name);
    setEmail(user.email);
    setPassword('');
    setUserRole(user.role);
    setSelectedRoleIds(user.roles.map((roleItem) => roleItem.id));
    setSelectedLibraryIds(user.libraries.map((library) => library.id));
    setIsActive(user.is_active);
    setError('');
    setSuccess('');
    setIsModalOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || isSubmitting) {
      return;
    }

    const payload: UserCreateInput = {
      full_name: fullName.trim(),
      email: email.trim().toLowerCase(),
      password,
      role: userRole,
      role_ids: selectedRoleIds,
      library_ids: selectedLibraryIds,
      is_active: isActive
    };

    setIsSubmitting(true);
    setError('');
    setSuccess('');

    try {
      if (modalMode === 'edit' && editingUserId) {
        await updateUser(editingUserId, {
          full_name: payload.full_name,
          email: payload.email,
          ...(payload.password ? { password: payload.password } : {}),
          role: payload.role,
          role_ids: payload.role_ids,
          library_ids: payload.library_ids,
          is_active: payload.is_active
        });
        setSuccess('Usuário atualizado com sucesso.');
      } else {
        await createUser(payload);
        setSuccess('Usuário criado com sucesso.');
      }
      setIsModalOpen(false);
      resetModal();
      await loadData();
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        setError('E-mail já cadastrado no tenant.');
      } else {
        setError('Não foi possível salvar o usuário.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(userId: number) {
    if (!window.confirm('Deseja realmente excluir este usuário?')) {
      return;
    }

    try {
      await deleteUser(userId);
      setSuccess('Usuário removido com sucesso.');
      await loadData();
    } catch {
      setError('Não foi possível remover o usuário.');
    }
  }

  const selectedRolesPermissions = metadata.roles
    .filter((roleItem) => selectedRoleIds.includes(roleItem.id))
    .flatMap((roleItem) => roleItem.permission_codes);

  return (
    <ProtectedRoute>
      <AppShell
        role={role ?? 'member'}
        title="Usuários"
        subtitle="Gestão institucional de usuários com RBAC e acesso multi-biblioteca por tenant."
      >
        {!hasPermission('users.read', permissions) ? (
          <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            Seu perfil não possui a permissão <strong>users.read</strong> para visualizar este módulo.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border bg-white p-4">
              <div>
                <h3 className="font-semibold text-slate-900">Usuários do tenant</h3>
                <p className="text-xs text-slate-500">CRUD completo com escopo por biblioteca.</p>
              </div>
              {hasPermission('users.create', permissions) ? (
                <button
                  type="button"
                  onClick={openCreateModal}
                  className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
                >
                  Novo usuário
                </button>
              ) : null}
            </div>

            {success ? <p className="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">{success}</p> : null}
            {error ? <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-700">{error}</p> : null}

            <DataTable
              columns={[
                { key: 'id', label: 'ID' },
                { key: 'full_name', label: 'Nome' },
                { key: 'email', label: 'Email' },
                { key: 'role', label: 'Role base' },
                { key: 'libraries', label: 'Bibliotecas' },
                { key: 'status', label: 'Status' },
                { key: 'permissions', label: 'Permissões (RBAC)' }
              ]}
              description="Controle de acesso institucional com RBAC e multi-library."
              rows={rows}
              searchableFields={['full_name', 'email', 'role', 'libraries', 'status', 'permissions']}
              title="Usuários"
            />

            {hasPermission('users.update', permissions) || hasPermission('users.delete', permissions) ? (
              <div className="rounded-lg border bg-white p-4">
                <h4 className="mb-2 text-sm font-semibold text-slate-900">Ações rápidas</h4>
                <ul className="space-y-2">
                  {users.map((user) => (
                    <li key={user.id} className="flex items-center justify-between rounded border px-3 py-2">
                      <span className="text-sm text-slate-700">{user.full_name} ({user.email})</span>
                      <div className="flex gap-2">
                        {hasPermission('users.update', permissions) ? (
                          <button type="button" className="rounded border px-3 py-1 text-xs" onClick={() => openEditModal(user)}>
                            Editar
                          </button>
                        ) : null}
                        {hasPermission('users.delete', permissions) ? (
                          <button
                            type="button"
                            className="rounded border border-rose-300 px-3 py-1 text-xs text-rose-600"
                            onClick={() => void handleDelete(user.id)}
                          >
                            Excluir
                          </button>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}

        {isModalOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
            <div className="w-full max-w-2xl rounded-xl border bg-white p-5 shadow-xl">
              <h4 className="text-lg font-semibold text-slate-900">
                {modalMode === 'edit' ? 'Editar usuário' : 'Novo usuário'}
              </h4>
              <form className="mt-4 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className="text-sm text-slate-600">Nome</label>
                    <input
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-sm text-slate-600">Email</label>
                    <input
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      type="email"
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm text-slate-600">Senha {modalMode === 'edit' ? '(opcional para alterar)' : ''}</label>
                  <input
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    type="password"
                    minLength={6}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    required={modalMode === 'create'}
                  />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className="text-sm text-slate-600">Role base</label>
                    <select
                      value={userRole}
                      onChange={(event) => setUserRole(event.target.value as UserRole)}
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    >
                      {roleOptions.map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-slate-600">Status</label>
                    <select
                      value={isActive ? 'active' : 'inactive'}
                      onChange={(event) => setIsActive(event.target.value === 'active')}
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    >
                      <option value="active">Ativo</option>
                      <option value="inactive">Inativo</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-sm text-slate-600">Roles (RBAC)</label>
                  <select
                    multiple
                    value={selectedRoleIds.map(String)}
                    onChange={(event) => {
                      const ids = Array.from(event.currentTarget.selectedOptions).map((option) => Number(option.value));
                      setSelectedRoleIds(ids);
                    }}
                    className="mt-1 h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  >
                    {metadata.roles.map((roleItem) => (
                      <option key={roleItem.id} value={roleItem.id}>{roleItem.name} ({roleItem.code})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-sm text-slate-600">Bibliotecas (multi-library)</label>
                  <select
                    multiple
                    value={selectedLibraryIds.map(String)}
                    onChange={(event) => {
                      const ids = Array.from(event.currentTarget.selectedOptions).map((option) => Number(option.value));
                      setSelectedLibraryIds(ids);
                    }}
                    className="mt-1 h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    required
                  >
                    {metadata.libraries.map((library) => (
                      <option key={library.id} value={library.id}>{library.name} ({library.code})</option>
                    ))}
                  </select>
                </div>

                <div className="rounded-md border bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-slate-600">Permissões RBAC selecionadas</p>
                  <p className="mt-1 text-xs text-slate-700">{Array.from(new Set(selectedRolesPermissions)).join(', ') || 'Nenhuma permissão selecionada'}</p>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIsModalOpen(false);
                      resetModal();
                    }}
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm"
                    disabled={isSubmitting}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={!canSubmit || isSubmitting}
                    className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-60"
                  >
                    {isSubmitting ? 'Salvando...' : 'Salvar usuário'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : null}
      </AppShell>
    </ProtectedRoute>
  );
}
