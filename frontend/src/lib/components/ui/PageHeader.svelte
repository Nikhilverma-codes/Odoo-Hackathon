<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/format';
	import Icon from './Icon.svelte';

	interface Props {
		title: string;
		description?: string;
		actions?: Snippet;
		backHref?: string;
		backLabel?: string;
		class?: string;
	}

	let {
		title,
		description,
		actions,
		backHref,
		backLabel = 'Back',
		class: extra = ''
	}: Props = $props();
</script>

<div class={cn('flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between', extra)}>
	<div class="min-w-0">
		{#if backHref}
			<a
				href={backHref}
				class="mb-2 inline-flex items-center gap-1 text-xs font-medium text-slate-500 transition hover:text-brand-600"
			>
				<Icon name="arrow-left" size={14} />
				{backLabel}
			</a>
		{/if}
		<h1 class="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
		{#if description}
			<p class="mt-1 max-w-2xl text-sm text-slate-500">{description}</p>
		{/if}
	</div>
	{#if actions}
		<div class="flex shrink-0 flex-wrap items-center gap-2">
			{@render actions()}
		</div>
	{/if}
</div>
