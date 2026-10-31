<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { auth } from '#lib/auth/auth.svelte';
	import { homeFor } from '#lib/auth/permissions';

	onMount(() => {
		goto(auth.isAuthenticated ? homeFor(auth.role) : '/login', { replaceState: true });
	});
</script>

<div class="flex min-h-screen items-center justify-center bg-slate-50">
	<span class="h-8 w-8 animate-spin rounded-full border-2 border-brand-200 border-t-brand-600"
	></span>
</div>
