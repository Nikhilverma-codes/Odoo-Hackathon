<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/format';

	type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success';
	type Size = 'sm' | 'md' | 'lg' | 'icon';

	interface Props {
		variant?: Variant;
		size?: Size;
		type?: 'button' | 'submit' | 'reset';
		href?: string;
		disabled?: boolean;
		class?: string;
		title?: string;
		onclick?: (event: MouseEvent) => void;
		children: Snippet;
	}

	let {
		variant = 'primary',
		size = 'md',
		type = 'button',
		href,
		disabled = false,
		class: extra = '',
		title,
		onclick,
		children
	}: Props = $props();

	const base =
		'inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 disabled:cursor-not-allowed disabled:opacity-50';

	const variants: Record<Variant, string> = {
		primary: 'bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800',
		secondary: 'bg-slate-900 text-white shadow-sm hover:bg-slate-800',
		outline:
			'border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50',
		ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
		danger: 'bg-rose-600 text-white shadow-sm hover:bg-rose-700',
		success: 'bg-emerald-600 text-white shadow-sm hover:bg-emerald-700'
	};

	const sizes: Record<Size, string> = {
		sm: 'h-8 px-3 text-xs',
		md: 'h-10 px-4 text-sm',
		lg: 'h-11 px-5 text-sm',
		icon: 'h-9 w-9'
	};

	let classes = $derived(cn(base, variants[variant], sizes[size], extra));
</script>

{#if href}
	<a {href} class={classes} {title}>{@render children()}</a>
{:else}
	<button {type} {disabled} {title} {onclick} class={classes}>{@render children()}</button>
{/if}
