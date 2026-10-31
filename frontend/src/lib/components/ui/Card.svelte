<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/format';

	interface Props {
		padded?: boolean;
		class?: string;
		children: Snippet;
	}

	let { padded = true, class: extra = '', children }: Props = $props();
</script>

<div
	class={cn(
		'rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-900/[0.03]',
		padded && 'p-5',
		extra
	)}
>
	{@render children()}
</div>
