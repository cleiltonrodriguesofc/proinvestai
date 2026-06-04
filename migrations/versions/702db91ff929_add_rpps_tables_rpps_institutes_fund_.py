"""add rpps tables: rpps_institutes, fund_positions, fund_quotes, portfolio_snapshots

Revision ID: 702db91ff929
Revises: 3c234fbff4cd
Create Date: 2026-06-03 21:18:08.329980

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '702db91ff929'
down_revision = '3c234fbff4cd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create rpps_institutes table (one RPPS institute per user account)
    op.create_table(
        'rpps_institutes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('cnpj', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('municipality', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('type_regime', sa.String(), nullable=False),
        sa.Column('total_assets', sa.Numeric(), nullable=True),
        sa.Column('actuarial_target_index', sa.String(), nullable=True),
        sa.Column('actuarial_target_rate', sa.Numeric(), nullable=True),
        sa.Column('pro_gestao_level', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rpps_institutes_cnpj'), 'rpps_institutes', ['cnpj'], unique=True)

    # Create fund_positions table (individual fund holdings per institute)
    op.create_table(
        'fund_positions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rpps_id', sa.UUID(), nullable=False),
        sa.Column('cnpj_fund', sa.String(), nullable=False),
        sa.Column('name_fund', sa.String(), nullable=False),
        sa.Column('segment_cmn', sa.String(), nullable=False),
        sa.Column('regulatory_article', sa.String(), nullable=True),
        sa.Column('benchmark', sa.String(), nullable=True),
        sa.Column('current_balance', sa.Numeric(), nullable=True),
        sa.Column('weight_pct', sa.Numeric(), nullable=True),
        sa.Column('liquidity_days', sa.Numeric(), nullable=True),
        sa.Column('monthly_return_pct', sa.Numeric(), nullable=True),
        sa.Column('admin_fee_pct', sa.Numeric(), nullable=True),
        sa.Column('is_legacy', sa.Boolean(), nullable=True),
        sa.Column('maturity_date', sa.Date(), nullable=True),
        sa.Column('date_entry', sa.Date(), nullable=True),
        sa.Column('manager_name', sa.String(), nullable=True),
        sa.Column('admin_name', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['rpps_id'], ['rpps_institutes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_fund_positions_cnpj_fund'), 'fund_positions', ['cnpj_fund'], unique=False)

    # Create fund_quotes table (historical NAV per fund CNPJ)
    op.create_table(
        'fund_quotes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('cnpj_fund', sa.String(), nullable=False),
        sa.Column('quote_date', sa.Date(), nullable=False),
        sa.Column('nav_per_share', sa.Numeric(), nullable=False),
        sa.Column('total_assets', sa.Numeric(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_fund_quotes_cnpj_fund'), 'fund_quotes', ['cnpj_fund'], unique=False)

    # Create portfolio_snapshots table (periodic portfolio state per institute)
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rpps_id', sa.UUID(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=True),
        sa.Column('total_value', sa.Numeric(), nullable=True),
        sa.Column('compliance_status', sa.String(), nullable=True),
        sa.Column('positions_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['rpps_id'], ['rpps_institutes.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('portfolio_snapshots')
    op.drop_index(op.f('ix_fund_quotes_cnpj_fund'), table_name='fund_quotes')
    op.drop_table('fund_quotes')
    op.drop_index(op.f('ix_fund_positions_cnpj_fund'), table_name='fund_positions')
    op.drop_table('fund_positions')
    op.drop_index(op.f('ix_rpps_institutes_cnpj'), table_name='rpps_institutes')
    op.drop_table('rpps_institutes')
