// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React from 'react';
import './augmentor-brand.css';
/** Original website motion in the supplier's decorative brand seat. */
export function AugmentorBrand({size=24}){
 // DSH clips its 24px brand row; reserve room for the original rotating outline.
 const outline=Math.round(size*.8);
 return <span className="augmentor-brand" style={{width:size,height:size}} aria-hidden="true"><span className="brand-orb augmentor-brand-orb" style={{width:outline,height:outline}} aria-hidden="true"/></span>;
}
