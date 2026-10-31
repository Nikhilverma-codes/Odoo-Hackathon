<script lang="ts">
	import Icon from './ui/Icon.svelte';
	import { cn } from '#lib/utils/format';

	interface Props {
		href?: string;
		compact?: boolean;
		class?: string;
	}

	let { href = '/', compact = false, class: extra = '' }: Props = $props();
</script>

<a {href} class={cn('inline-flex items-center gap-2.5', extra)}>
	<span
		class="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 text-white shadow-lg shadow-brand-600/25"
	>
		<Icon name="sparkles" size={18} />
	</span>
	{#if !compact}
		<span class="leading-none">
			<span class="block text-[15px] font-bold tracking-tight text-slate-900">Brightloop</span>
			<span class="mt-1 block text-[9px] font-semibold tracking-[0.2em] text-slate-400 uppercase"
				>Billing OS</span
			>
		</span>
	{/if}
</a>
