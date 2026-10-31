<script lang="ts">
	import Button from './Button.svelte';
	import Modal from './Modal.svelte';
	import Icon from './Icon.svelte';

	interface Props {
		open?: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		tone?: 'danger' | 'primary';
		loading?: boolean;
		onconfirm: () => void;
		oncancel: () => void;
	}

	let {
		open = false,
		title,
		message,
		confirmLabel = 'Confirm',
		tone = 'danger',
		loading = false,
		onconfirm,
		oncancel
	}: Props = $props();
</script>

<Modal {open} {title} size="sm" onclose={oncancel}>
	<div class="flex gap-3">
		<div
			class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
			class:bg-rose-50={tone === 'danger'}
			class:text-rose-600={tone === 'danger'}
			class:bg-brand-50={tone === 'primary'}
			class:text-brand-600={tone === 'primary'}
		>
			<Icon name="exclamation" size={20} />
		</div>
		<p class="pt-1 text-sm text-slate-600">{message}</p>
	</div>

	{#snippet footer()}
		<Button variant="outline" onclick={oncancel} disabled={loading}>Cancel</Button>
		<Button
			variant={tone === 'danger' ? 'danger' : 'primary'}
			onclick={onconfirm}
			disabled={loading}
		>
			{loading ? 'Working…' : confirmLabel}
		</Button>
	{/snippet}
</Modal>
