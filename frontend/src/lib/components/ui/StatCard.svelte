<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/format';
	import Icon from './Icon.svelte';

	type Tone = 'brand' | 'emerald' | 'amber' | 'rose' | 'sky' | 'violet';

	interface Props {
		label: string;
		value: string;
		hint?: string;
		icon?: string;
		tone?: Tone;
		trend?: number;
		footer?: Snippet;
	}

	let { label, value, hint, icon = 'chart', tone = 'brand', trend, footer }: Props = $props();

	const tones: Record<Tone, { wrap: string; icon: string }> = {
		brand: { wrap: 'bg-brand-50 text-brand-600', icon: 'bg-brand-100/70' },
		emerald: { wrap: 'bg-emerald-50 text-emerald-600', icon: 'bg-emerald-100/70' },
		amber: { wrap: 'bg-amber-50 text-amber-600', icon: 'bg-amber-100/70' },
		rose: { wrap: 'bg-rose-50 text-rose-600', icon: 'bg-rose-100/70' },
		sky: { wrap: 'bg-sky-50 text-sky-600', icon: 'bg-sky-100/70' },
		violet: { wrap: 'bg-violet-50 text-violet-600', icon: 'bg-violet-100/70' }
	};
</script>

<div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/[0.03]">
	<div class="flex items-start justify-between gap-3">
		<div class="min-w-0">
			<p class="truncate text-sm font-medium text-slate-500">{label}</p>
			<p class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
		</div>
		<div
			class={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl', tones[tone].wrap)}
		>
			<Icon name={icon} size={18} />
		</div>
	</div>
	<div class="mt-3 flex items-center gap-2">
		{#if typeof trend === 'number'}
			<span
				class={cn(
					'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-semibold',
					trend >= 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
				)}
			>
				<Icon name={trend >= 0 ? 'arrow-up' : 'arrow-down'} size={11} stroke={2.4} />
				{Math.abs(trend).toFixed(1)}%
			</span>
		{/if}
		{#if hint}
			<p class="truncate text-xs text-slate-400">{hint}</p>
		{/if}
	</div>
	{#if footer}
		<div class="mt-3">{@render footer()}</div>
	{/if}
</div>
