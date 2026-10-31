<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import Toaster from '#lib/components/ui/Toaster.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Brightloop · Subscription Management</title>
	<meta
		name="description"
		content="Brightloop runs plans, subscriptions, invoicing and recurring revenue in one place."
	/>
</svelte:head>

{@render children()}
<Toaster />
