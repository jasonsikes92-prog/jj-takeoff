"""Preliminary straight-flight geometry, separate from structural and stock design."""
import math


def straight_stair_reference(total_rise_in, width_in, *, max_riser_in, going_in,
                             landing_depth_in):
    values=(total_rise_in,width_in,max_riser_in,going_in,landing_depth_in)
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values):
        raise ValueError('Stair dimensions must be finite positive numbers')
    risers=math.ceil(total_rise_in/max_riser_in)
    treads=risers-1  # Upper deck serves as the top landing.
    return {'riser_count':risers,'equal_riser_height_in':total_rise_in/risers,
        'separate_tread_count':treads,'going_in':going_in,
        'horizontal_run_in':treads*going_in,'width_in':width_in,
        'projected_tread_area_sf':treads*going_in*width_in/144,
        'bottom_landing_reference_sf':width_in*landing_depth_in/144,
        'landing_depth_in':landing_depth_in,'stock_order_released':False,
        'structural_design_verified':False}
