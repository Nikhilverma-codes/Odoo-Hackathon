<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { auth } from '#lib/auth/auth.svelte';
	import { homeFor } from '#lib/auth/permissions';
	import Button from '#lib/components/ui/Button.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import { toasts } from '#lib/stores/toasts.svelte';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	const demoAccounts = [
		{
			role: 'Admin',
			email: 'admin@brightloop.io',
			password: 'Admin@123',
			detail: 'Full system access'
		},
		{
			role: 'Customer',
			email: 'priya@nimbus.co',
			password: 'Customer@123',
			detail: 'View your services and invoices'
		}
	];

	function submit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		loading = true;
		const result = auth.login(email, password);
		loading = false;
		if (!result.ok) {
			error = result.error ?? 'Unable to sign in.';
			return;
		}
		toasts.success(`Welcome back, ${result.user?.name.split(' ')[0] ?? 'there'}!`);
		const redirect = page.url.searchParams.get('redirect');
		goto(redirect || homeFor(auth.role), { replaceState: true });
	}

	function useDemo(account: (typeof demoAccounts)[number]) {
		email = account.email;
		password = account.password;
		error = '';
	}
</script>

<svelte:head>
	<title>Sign in · Brightloop</title>
</svelte:head>

<div>
	<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Welcome back</h1>
	<p class="mt-1 text-sm text-slate-500">Sign in to manage your subscriptions and billing.</p>

	{#if error}
		<div
			class="mt-5 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-700"
		>
			<Icon name="exclamation" size={16} class="mt-0.5 shrink-0" />
			<span>{error}</span>
		</div>
	{/if}

	<form class="mt-6 space-y-4" onsubmit={submit}>
		<Input
			label="Email address"
			type="email"
			placeholder="you@company.com"
			autocomplete="email"
			icon="mail"
			required
			bind:value={email}
		/>
		<Input
			label="Password"
			type="password"
			placeholder="Your password"
			autocomplete="current-password"
			icon="lock"
			required
			bind:value={password}
		/>

		<Button type="submit" size="lg" class="w-full" disabled={loading}>
			{loading ? 'Signing in…' : 'Sign in'}
			<Icon name="arrow-right" size={16} />
		</Button>
	</form>

	<div class="mt-8">
		<div class="flex items-center gap-3">
			<div class="h-px flex-1 bg-slate-200"></div>
			<span class="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
				Demo accounts
			</span>
			<div class="h-px flex-1 bg-slate-200"></div>
		</div>

		<div class="mt-4 space-y-2">
			{#each demoAccounts as account (account.role)}
				<button
					type="button"
					class="flex w-full items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left transition hover:border-brand-300 hover:bg-brand-50/40"
					onclick={() => useDemo(account)}
				>
					<div>
						<p class="text-sm font-semibold text-slate-800">{account.role}</p>
						<p class="text-xs text-slate-400">{account.detail} · {account.email}</p>
					</div>
					<Icon name="arrow-right" size={16} class="text-slate-400" />
				</button>
			{/each}
		</div>
		<p class="mt-3 text-center text-[11px] text-slate-400">
			Click a demo account to fill the form, then sign in.
		</p>
	</div>
</div>
