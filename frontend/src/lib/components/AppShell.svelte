<script lang="ts">
	import type { Snippet } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { auth } from '#lib/auth/auth.svelte';
	import { homeFor } from '#lib/auth/permissions';
	import { customerById } from '#lib/data/selectors';
	import { db } from '#lib/data/store.svelte';
	import { sectionsFor, titleFor } from '#lib/nav';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { formatDate } from '#lib/utils/date';
	import { cn } from '#lib/utils/format';
	import BrandMark from './BrandMark.svelte';
	import Avatar from './ui/Avatar.svelte';
	import Icon from './ui/Icon.svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let sidebarOpen = $state(false);
	let pathname = $derived(page.url.pathname);
	let sections = $derived(sectionsFor(auth.role));
	let title = $derived(titleFor(pathname));
	let user = $derived(auth.user);
	let company = $derived(
		user?.customerId
			? (customerById(db.data, user.customerId)?.company ?? 'Customer portal')
			: 'Brightloop Software'
	);
	let invoicesHref = $derived(auth.role === 'customer' ? '/portal/invoices' : '/invoices');
	let invoicesLabel = $derived(auth.role === 'customer' ? 'My invoices' : 'Invoices');
	let today = $derived(formatDate(new Date().toISOString()));

	$effect(() => {
		void pathname;
		sidebarOpen = false;
	});

	function isActive(href: string): boolean {
		if (href === '/dashboard' || href === '/portal') return pathname === href;
		return pathname === href || pathname.startsWith(`${href}/`);
	}

	function signOut() {
		auth.logout();
		toasts.info('Signed out.');
		goto('/login');
	}
</script>

<div class="min-h-screen bg-slate-50">
	{#if sidebarOpen}
		<button
			type="button"
			class="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-sm lg:hidden"
			aria-label="Close navigation"
			onclick={() => (sidebarOpen = false)}
		></button>
	{/if}

	<aside
		class={cn(
			'no-print fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-200 lg:translate-x-0',
			sidebarOpen ? 'translate-x-0' : '-translate-x-full'
		)}
	>
		<div class="flex h-16 shrink-0 items-center justify-between border-b border-slate-100 px-5">
			<BrandMark href={homeFor(auth.role)} />
			<button
				type="button"
				class="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 lg:hidden"
				aria-label="Close navigation"
				onclick={() => (sidebarOpen = false)}
			>
				<Icon name="close" size={18} />
			</button>
		</div>

		<nav class="flex-1 scrollbar-thin space-y-6 overflow-y-auto px-3 py-5">
			{#each sections as section (section.title)}
				<div>
					<p class="px-3 pb-2 text-[10px] font-semibold tracking-[0.16em] text-slate-400 uppercase">
						{section.title}
					</p>
					<ul class="space-y-0.5">
						{#each section.items as item (item.href)}
							<li>
								<a
									href={item.href}
									class={cn(
										'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
										isActive(item.href)
											? 'bg-brand-50 text-brand-700'
											: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
									)}
								>
									<Icon
										name={item.icon}
										size={17}
										class={isActive(item.href) ? 'text-brand-600' : 'text-slate-400'}
									/>
									{item.label}
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</nav>

		<div class="shrink-0 border-t border-slate-100 p-3">
			<div class="flex items-center gap-3 rounded-xl px-2 py-2">
				<Avatar name={user?.name ?? 'User'} size="sm" />
				<div class="min-w-0 flex-1">
					<p class="truncate text-sm font-semibold text-slate-800">{user?.name ?? '—'}</p>
					<p class="truncate text-[11px] text-slate-400 capitalize">{auth.role} · {company}</p>
				</div>
				<button
					type="button"
					class="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
					title="Sign out"
					aria-label="Sign out"
					onclick={signOut}
				>
					<Icon name="logout" size={16} />
				</button>
			</div>
		</div>
	</aside>

	<div class="lg:pl-64 print:pl-0">
		<header
			class="no-print sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/80 px-4 backdrop-blur sm:px-6 lg:px-8"
		>
			<button
				type="button"
				class="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-100 lg:hidden"
				aria-label="Open navigation"
				onclick={() => (sidebarOpen = true)}
			>
				<Icon name="menu" size={20} />
			</button>
			<div class="min-w-0 flex-1">
				<p class="truncate text-sm font-semibold text-slate-800">{title}</p>
				<p class="hidden text-[11px] text-slate-400 sm:block">{today}</p>
			</div>

			<a
				href={invoicesHref}
				class="hidden items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:border-slate-300 hover:text-slate-700 sm:inline-flex"
			>
				<Icon name="receipt" size={14} />
				{invoicesLabel}
			</a>

			<div class="flex items-center gap-2 border-l border-slate-200 pl-3">
				<Avatar name={user?.name ?? 'User'} size="xs" />
				<span class="hidden text-xs font-medium text-slate-600 md:block">{user?.name}</span>
			</div>
		</header>

		<main
			class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 print:max-w-none print:px-0 print:py-0"
		>
			{@render children()}
		</main>
	</div>
</div>
