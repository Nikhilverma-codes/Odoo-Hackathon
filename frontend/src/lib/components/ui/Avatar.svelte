<script lang="ts">
	import { avatarColor, cn, initials } from '#lib/utils/format';

	interface Props {
		name: string;
		size?: 'xs' | 'sm' | 'md' | 'lg';
		class?: string;
	}

	let { name, size = 'md', class: extra = '' }: Props = $props();

	const sizes = {
		xs: 'h-7 w-7 text-[10px]',
		sm: 'h-8 w-8 text-xs',
		md: 'h-10 w-10 text-sm',
		lg: 'h-14 w-14 text-lg'
	};
</script>

<div
	class={cn(
		'flex shrink-0 items-center justify-center rounded-full font-semibold',
		sizes[size],
		avatarColor(name),
		extra
	)}
	aria-hidden="true"
>
	{initials(name)}
</div>
