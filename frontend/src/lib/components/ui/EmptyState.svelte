<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	interface Props {
		icon?: string;
		title: string;
		description?: string;
		action?: Snippet;
	}

	let { icon = 'box', title, description, action }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center px-6 py-14 text-center">
	<div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
		<Icon name={icon} size={22} />
	</div>
	<p class="mt-4 text-sm font-semibold text-slate-900">{title}</p>
	{#if description}
		<p class="mt-1 max-w-sm text-sm text-slate-500">{description}</p>
	{/if}
	{#if action}
		<div class="mt-4">{@render action()}</div>
	{/if}
</div>
