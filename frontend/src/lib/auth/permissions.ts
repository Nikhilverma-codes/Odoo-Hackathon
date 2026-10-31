import type { Role } from '#lib/data/types';

export function homeFor(role: Role | null): string {
	return role === 'customer' ? '/portal' : '/dashboard';
}

export function isAdmin(role: Role | null): boolean {
	return role === 'admin';
}

export function canAccess(pathname: string, role: Role | null): boolean {
	if (!role) return false;
	const isPortal = pathname === '/portal' || pathname.startsWith('/portal/');
	if (role === 'customer') return isPortal;
	if (role === 'admin') return !isPortal;
	return false;
}
