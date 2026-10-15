{% snapshot snap_fields %}

{{
    config(
        target_schema='snapshots',
        unique_key='field_id',
        strategy='check',
        updated_at='warehouse_observed_at',
        check_cols=[
            'farm_id',
            'field_name',
            'area_hectares',
            'crop_type',
            'soil_type',
            'irrigation_type',
            'status',
            'created_at',
            'effective_from',
            'updated_at'
        ]
    )
}}

select
    field_id,
    farm_id,
    field_name,
    area_hectares,
    crop_type,
    soil_type,
    irrigation_type,
    status,
    created_at,
    effective_from,
    updated_at,
    ingested_at,
    current_timestamp as warehouse_observed_at

from {{ ref('stg_fields') }}

{% endsnapshot %}