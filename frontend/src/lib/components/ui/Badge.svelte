<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/format';

	export type Tone = 'slate' | 'blue' | 'violet' | 'green' | 'amber' | 'red' | 'brand';

	interface Props {
		tone?: Tone;
		dot?: boolean;
		class?: string;
		children: Snippet;
	}

	let { tone = 'slate', dot = false, class: extra = '', children }: Props = $props();

	const tones: Record<Tone, string> = {
		slate: 'bg-slate-100 text-slate-700 ring-slate-200',
		blue: 'bg-sky-50 text-sky-700 ring-sky-200',
		violet: 'bg-violet-50 text-violet-700 ring-violet-200',
		green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
		amber: 'bg-amber-50 text-amber-700 ring-amber-200',
		red: 'bg-rose-50 text-rose-700 ring-rose-200',
		brand: 'bg-brand-50 text-brand-700 ring-brand-200'
	};

	const dots: Record<Tone, string> = {
		slate: 'bg-slate-400',
		blue: 'bg-sky-500',
		violet: 'bg-violet-500',
		green: 'bg-emerald-500',
		amber: 'bg-amber-500',
		red: 'bg-rose-500',
		brand: 'bg-brand-500'
	};
</script>

<span
	class={cn(
		'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
		tones[tone],
		extra
	)}
>
	{#if dot}
		<span class={cn('h-1.5 w-1.5 rounded-full', dots[tone])}></span>
	{/if}
	{@render children()}
</span>
