<script lang="ts">
	import Badge, { type Tone } from './Badge.svelte';

	interface Props {
		status: string;
		dot?: boolean;
	}

	let { status, dot = true }: Props = $props();

	const tones: Record<string, Tone> = {
		draft: 'slate',
		quotation: 'blue',
		confirmed: 'violet',
		active: 'green',
		paused: 'amber',
		closed: 'slate',
		paid: 'green',
		cancelled: 'red',
		overdue: 'red'
	};

	const labels: Record<string, string> = {
		draft: 'Draft',
		quotation: 'Quotation',
		confirmed: 'Confirmed',
		active: 'Active',
		paused: 'Paused',
		closed: 'Closed',
		paid: 'Paid',
		cancelled: 'Cancelled',
		overdue: 'Overdue'
	};

	let tone = $derived(tones[status] ?? 'slate');
	let label = $derived(labels[status] ?? status);
</script>

<Badge {tone} {dot}>{label}</Badge>
