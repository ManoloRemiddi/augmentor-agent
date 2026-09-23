// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {Type} from 'typebox';
export const desktopTools = [
  {name: 'desktop_connect', method: 'connect', description: 'Request desktop sharing through OS consent. Request only once; never retry declined consent.', parameters: Type.Object({})},
  {name: 'desktop_snapshot', method: 'capture', description: 'Capture the consented desktop with a fresh single-use action token. Screenshot coordinates are in returned image pixels. Capture before each action and afterward to verify.', parameters: Type.Object({})},
  {name: 'desktop_action', method: 'action', description: 'Dispatch one input against the fresh screenshot token. Dispatch does not prove success. Refused or unknown outcomes end the task.', parameters: Type.Object({token: Type.String({maxLength: 256}), kind: Type.Union([Type.Literal('click'), Type.Literal('key'), Type.Literal('type')]), x: Type.Optional(Type.Number()), y: Type.Optional(Type.Number()), keys: Type.Optional(Type.Array(Type.String({maxLength: 64}), {maxItems: 3})), text: Type.Optional(Type.String({maxLength: 256}))})},
  {name: 'desktop_stop', method: 'stop', description: 'Release inputs and close this task’s desktop sharing connection.', parameters: Type.Object({})},
] as const;
