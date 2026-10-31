<script lang="ts">
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { auth } from '#lib/auth/auth.svelte';
	import { canAccess, homeFor } from '#lib/auth/permissions';
	import AppShell from '#lib/components/AppShell.svelte';

	let { children }: { children: Snippet } = $props();

	let pathname = $derived(page.url.pathname);
	let user = $derived(auth.user);
	let ready = $derived(auth.ready);
	let allowed = $derived(!!user && ready && canAccess(pathname, auth.role));

	onMount(() => {
		void auth.initialize();
	});

	$effect(() => {
		if (!ready) return;
		if (!user) {
			goto(`/login?redirect=${encodeURIComponent(pathname)}`, { replaceState: true });
			return;
		}
		if (!canAccess(pathname, auth.role)) {
			goto(homeFor(auth.role), { replaceState: true });
		}
	});
</script>

{#if allowed}
	<AppShell>
		{@render children()}
	</AppShell>
{:else}
	<div class="flex min-h-screen items-center justify-center bg-slate-50">
		<span class="h-8 w-8 animate-spin rounded-full border-2 border-brand-200 border-t-brand-600"
		></span>
	</div>
{/if}
