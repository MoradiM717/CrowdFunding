"""Django admin configuration for blockchain models."""

import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from core.models import Chain, SyncState, Campaign, Contribution, Event
from core.utils.formatting import wei_to_eth, timestamp_to_datetime

# Customize admin site
admin.site.site_header = "Crowdfunding Backend Administration"
admin.site.site_title = "Crowdfunding Admin"
admin.site.index_title = "Welcome to Crowdfunding Backend Administration"


@admin.register(Chain)
class ChainAdmin(admin.ModelAdmin):
    """Admin for Chain model."""
    
    list_display = ['id', 'name', 'chain_id', 'rpc_url', 'created_at', 'updated_at']
    list_filter = ['chain_id']
    search_fields = ['name', 'chain_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Chain Info', {
            'fields': ('id', 'name', 'chain_id', 'rpc_url')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SyncState)
class SyncStateAdmin(admin.ModelAdmin):
    """Admin for SyncState model."""
    
    list_display = ['chain_id', 'chain_name', 'last_block', 'last_block_hash_short', 'updated_at']
    list_filter = ['chain_id']
    search_fields = ['chain_id', 'last_block_hash']
    readonly_fields = ['chain_id', 'updated_at']
    actions = ['reset_to_zero', 'reset_to_block_1']
    
    fieldsets = (
        ('Sync Info', {
            'fields': ('chain_id', 'last_block', 'last_block_hash')
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def chain_name(self, obj):
        """Display chain name."""
        return obj.chain.name if obj.chain else 'N/A'
    chain_name.short_description = 'Chain Name'
    
    def last_block_hash_short(self, obj):
        """Display shortened block hash."""
        if obj.last_block_hash:
            return f"{obj.last_block_hash[:10]}...{obj.last_block_hash[-8:]}"
        return 'N/A'
    last_block_hash_short.short_description = 'Last Block Hash'
    
    @admin.action(description='Reset sync state to block 0')
    def reset_to_zero(self, request, queryset):
        """Reset selected sync states to block 0."""
        updated = queryset.update(last_block=0, last_block_hash='')
        self.message_user(request, f'Reset {updated} sync state(s) to block 0.')
    
    @admin.action(description='Reset sync state to block 1')
    def reset_to_block_1(self, request, queryset):
        """Reset selected sync states to block 1."""
        updated = queryset.update(last_block=1, last_block_hash='')
        self.message_user(request, f'Reset {updated} sync state(s) to block 1.')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin for Campaign model."""
    
    list_display = [
        'address_short',
        'status',
        'creator_address_short',
        'goal_eth',
        'total_raised_eth',
        'progress_percent',
        'deadline_datetime',
        'withdrawn',
        'created_at'
    ]
    list_filter = ['status', 'withdrawn', 'factory_address']
    search_fields = ['address', 'creator_address', 'factory_address', 'cid']
    list_editable = ['status', 'withdrawn']
    readonly_fields = [
        'address',
        'factory_address',
        'creator_address',
        'goal_eth',
        'deadline_datetime',
        'total_raised_eth',
        'progress_percent',
        'withdrawn_amount_eth',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Campaign Info', {
            'fields': ('address', 'factory_address', 'creator_address', 'cid', 'status')
        }),
        ('Funding (Editable)', {
            'fields': (
                ('goal_wei', 'goal_eth'),
                ('total_raised_wei', 'total_raised_eth'),
                'progress_percent'
            )
        }),
        ('Withdrawal (Editable)', {
            'fields': ('withdrawn', ('withdrawn_amount_wei', 'withdrawn_amount_eth'))
        }),
        ('Timeline', {
            'fields': (('deadline_ts', 'deadline_datetime'), 'created_at', 'updated_at')
        }),
    )
    
    def address_short(self, obj):
        """Display shortened address."""
        return f"{obj.address[:10]}...{obj.address[-6:]}"
    address_short.short_description = 'Address'
    
    def creator_address_short(self, obj):
        """Display shortened creator address."""
        return f"{obj.creator_address[:10]}...{obj.creator_address[-6:]}"
    creator_address_short.short_description = 'Creator'
    
    def goal_eth(self, obj):
        """Display goal in ETH."""
        if obj.goal_wei:
            return f"{wei_to_eth(obj.goal_wei):.6f} ETH"
        return "0 ETH"
    goal_eth.short_description = 'Goal (ETH)'
    
    def total_raised_eth(self, obj):
        """Display total raised in ETH."""
        if obj.total_raised_wei:
            return f"{wei_to_eth(obj.total_raised_wei):.6f} ETH"
        return "0 ETH"
    total_raised_eth.short_description = 'Total Raised (ETH)'
    
    def progress_percent(self, obj):
        """Calculate and display progress percentage."""
        if obj.goal_wei and obj.goal_wei > 0:
            percent = (obj.total_raised_wei / obj.goal_wei) * 100
            color = 'green' if percent >= 100 else 'orange' if percent >= 50 else 'red'
            # Format percent first, then pass to format_html
            percent_str = f"{percent:.2f}%"
            return format_html(
                '<span style="color: {};">{}</span>',
                color,
                percent_str
            )
        return "0%"
    progress_percent.short_description = 'Progress'
    
    def deadline_datetime(self, obj):
        """Convert deadline timestamp to datetime."""
        dt = timestamp_to_datetime(obj.deadline_ts)
        if dt:
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        return 'N/A'
    deadline_datetime.short_description = 'Deadline'
    
    def withdrawn_amount_eth(self, obj):
        """Display withdrawn amount in ETH."""
        if obj.withdrawn_amount_wei:
            return f"{wei_to_eth(obj.withdrawn_amount_wei):.6f} ETH"
        return "0 ETH"
    withdrawn_amount_eth.short_description = 'Withdrawn Amount (ETH)'
    
    actions = ['mark_active', 'mark_failed', 'mark_success', 'reset_totals']
    
    @admin.action(description='Mark selected campaigns as ACTIVE')
    def mark_active(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f'Marked {updated} campaign(s) as ACTIVE.')
    
    @admin.action(description='Mark selected campaigns as FAILED')
    def mark_failed(self, request, queryset):
        updated = queryset.update(status='FAILED')
        self.message_user(request, f'Marked {updated} campaign(s) as FAILED.')
    
    @admin.action(description='Mark selected campaigns as SUCCESS')
    def mark_success(self, request, queryset):
        updated = queryset.update(status='SUCCESS')
        self.message_user(request, f'Marked {updated} campaign(s) as SUCCESS.')
    
    @admin.action(description='Reset total_raised_wei to 0')
    def reset_totals(self, request, queryset):
        updated = queryset.update(total_raised_wei=0)
        self.message_user(request, f'Reset totals for {updated} campaign(s).')


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    """Admin for Contribution model."""
    
    list_display = [
        'id',
        'campaign_address',
        'donor_address_short',
        'contributed_eth',
        'refunded_eth',
        'net_contributed_eth',
        'created_at'
    ]
    list_filter = ['campaign_address']
    search_fields = ['campaign_address__address', 'donor_address']
    readonly_fields = [
        'id',
        'contributed_eth',
        'refunded_eth',
        'net_contributed_eth',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Contribution Info', {
            'fields': ('id', 'campaign_address', 'donor_address')
        }),
        ('Amounts (Editable)', {
            'fields': (
                ('contributed_wei', 'contributed_eth'),
                ('refunded_wei', 'refunded_eth'),
                'net_contributed_eth'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def donor_address_short(self, obj):
        """Display shortened donor address."""
        return f"{obj.donor_address[:10]}...{obj.donor_address[-6:]}"
    donor_address_short.short_description = 'Donor'
    
    def contributed_eth(self, obj):
        """Display contributed amount in ETH."""
        if obj.contributed_wei:
            return f"{wei_to_eth(obj.contributed_wei):.6f} ETH"
        return "0 ETH"
    contributed_eth.short_description = 'Contributed (ETH)'
    
    def refunded_eth(self, obj):
        """Display refunded amount in ETH."""
        if obj.refunded_wei:
            return f"{wei_to_eth(obj.refunded_wei):.6f} ETH"
        return "0 ETH"
    refunded_eth.short_description = 'Refunded (ETH)'
    
    def net_contributed_eth(self, obj):
        """Calculate net contribution (contributed - refunded)."""
        net_wei = obj.contributed_wei - obj.refunded_wei
        if net_wei > 0:
            return f"{wei_to_eth(net_wei):.6f} ETH"
        return "0 ETH"
    net_contributed_eth.short_description = 'Net Contribution (ETH)'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin for Event model."""
    
    list_display = [
        'id',
        'chain_id',
        'event_name',
        'address_short',
        'block_number',
        'tx_hash_short',
        'log_index',
        'removed',
        'created_at'
    ]
    list_filter = ['event_name', 'removed', 'chain_id']
    search_fields = ['tx_hash', 'address__address', 'event_name']
    list_editable = ['removed']
    readonly_fields = [
        'id',
        'formatted_event_data',
        'created_at'
    ]
    
    fieldsets = (
        ('Event Info', {
            'fields': ('id', 'chain_id', 'event_name', 'removed')
        }),
        ('Blockchain Data (Editable)', {
            'fields': ('tx_hash', 'log_index', 'block_number', 'block_hash', 'address')
        }),
        ('Event Data', {
            'fields': ('event_data', 'formatted_event_data')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def address_short(self, obj):
        """Display shortened address."""
        if obj.address:
            addr = str(obj.address.address) if hasattr(obj.address, 'address') else str(obj.address)
            return f"{addr[:10]}...{addr[-6:]}"
        return 'N/A'
    address_short.short_description = 'Address'
    
    def tx_hash_short(self, obj):
        """Display shortened transaction hash."""
        if obj.tx_hash:
            return f"{obj.tx_hash[:10]}...{obj.tx_hash[-8:]}"
        return 'N/A'
    tx_hash_short.short_description = 'TX Hash'
    
    def formatted_event_data(self, obj):
        """Pretty-print JSON event data."""
        if not obj.event_data:
            return 'No event data'
        
        try:
            data = json.loads(obj.event_data)
            formatted = json.dumps(data, indent=2)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', formatted)
        except json.JSONDecodeError:
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', obj.event_data)
    formatted_event_data.short_description = 'Event Data (JSON)'
    
    actions = ['mark_removed', 'mark_not_removed', 'delete_selected_events']
    
    @admin.action(description='Mark selected events as removed')
    def mark_removed(self, request, queryset):
        updated = queryset.update(removed=True)
        self.message_user(request, f'Marked {updated} event(s) as removed.')
    
    @admin.action(description='Mark selected events as NOT removed')
    def mark_not_removed(self, request, queryset):
        updated = queryset.update(removed=False)
        self.message_user(request, f'Marked {updated} event(s) as not removed.')
    
    @admin.action(description='Delete selected events')
    def delete_selected_events(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Deleted {count} event(s).')

