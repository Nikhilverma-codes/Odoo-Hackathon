<script lang="ts">
	import type { FullAutoFill } from 'svelte/elements';
	import { cn } from '#lib/utils/format';
	import Icon from './Icon.svelte';

	interface Props {
		label?: string;
		hint?: string;
		error?: string;
		value?: string | number;
		type?: string;
		placeholder?: string;
		required?: boolean;
		disabled?: boolean;
		name?: string;
		autocomplete?: FullAutoFill;
		min?: string | number;
		max?: string | number;
		step?: string | number;
		icon?: string;
		class?: string;
		oninput?: (event: Event) => void;
	}

	let {
		label,
		hint,
		error,
		value = $bindable(''),
		type = 'text',
		placeholder,
		required = false,
		disabled = false,
		name,
		autocomplete,
		min,
		max,
		step,
		icon,
		class: extra = '',
		oninput
	}: Props = $props();
</script>

<label class={cn('block', extra)}>
	{#if label}
		<span class="mb-1.5 flex items-center gap-1 text-xs font-medium text-slate-600">
			{label}
			{#if required}<span class="text-rose-500">*</span>{/if}
		</span>
	{/if}
	<div class="relative">
		{#if icon}
			<span
				class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400"
			>
				<Icon name={icon} size={16} />
			</span>
		{/if}
		<input
			{type}
			{name}
			{placeholder}
			{required}
			{disabled}
			{autocomplete}
			{min}
			{max}
			{step}
			bind:value
			{oninput}
			class={cn(
				'w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition placeholder:text-slate-400 focus:ring-2 focus:outline-none disabled:bg-slate-50 disabled:text-slate-500',
				icon && 'pl-9',
				error
					? 'border-rose-300 focus:border-rose-400 focus:ring-rose-200'
					: 'border-slate-300 focus:border-brand-500 focus:ring-brand-500/20'
			)}
		/>
	</div>
	{#if error}
		<span class="mt-1 block text-xs text-rose-600">{error}</span>
	{:else if hint}
		<span class="mt-1 block text-xs text-slate-400">{hint}</span>
	{/if}
</label>
