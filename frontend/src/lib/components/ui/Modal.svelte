<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/format';
	import Icon from './Icon.svelte';

	interface Props {
		open?: boolean;
		title: string;
		description?: string;
		size?: 'sm' | 'md' | 'lg' | 'xl';
		onclose?: () => void;
		children: Snippet;
		footer?: Snippet;
	}

	let {
		open = false,
		title,
		description,
		size = 'md',
		onclose,
		children,
		footer
	}: Props = $props();

	const widths = {
		sm: 'max-w-md',
		md: 'max-w-xl',
		lg: 'max-w-3xl',
		xl: 'max-w-5xl'
	};

	function handleKey(event: KeyboardEvent) {
		if (open && event.key === 'Escape') onclose?.();
	}
</script>

<svelte:window onkeydown={handleKey} />

{#if open}
	<div class="fixed inset-0 z-50 overflow-y-auto">
		<button
			type="button"
			class="fixed inset-0 cursor-default bg-slate-900/40 backdrop-blur-sm"
			aria-label="Close dialog"
			onclick={() => onclose?.()}
		></button>
		<div class="relative flex min-h-full items-start justify-center p-4 sm:items-center">
			<div
				role="dialog"
				aria-modal="true"
				aria-label={title}
				class={cn(
					'relative my-8 w-full overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-slate-900/5',
					widths[size]
				)}
			>
				<div class="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-4">
					<div class="min-w-0">
						<h2 class="text-base font-semibold text-slate-900">{title}</h2>
						{#if description}
							<p class="mt-0.5 text-sm text-slate-500">{description}</p>
						{/if}
					</div>
					<button
						type="button"
						class="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
						aria-label="Close"
						onclick={() => onclose?.()}
					>
						<Icon name="close" size={18} />
					</button>
				</div>

				<div class="max-h-[70vh] overflow-y-auto px-6 py-5">
					{@render children()}
				</div>

				{#if footer}
					<div
						class="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 bg-slate-50 px-6 py-4"
					>
						{@render footer()}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
