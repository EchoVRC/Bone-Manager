bl_info = {
    "name": "Shapekey Transfer Tool",
    "author": "EchoVRC",
    "blender": (3, 3, 0),
    "version": (1, 0),
    "description": "Tool for transferring shapekeys between meshes with different topology",
    "location": "View3D > UI",
    "category": "3D View"
}

import bpy
from mathutils import Vector

disable_update = False

class STT_OriginalPosition(bpy.types.PropertyGroup):
    x: bpy.props.FloatProperty()
    y: bpy.props.FloatProperty()
    z: bpy.props.FloatProperty()

class STT_OriginalShapeKey(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    values: bpy.props.CollectionProperty(type=STT_OriginalPosition)
    value: bpy.props.FloatProperty()

class STT_ShapekeyItem(bpy.types.PropertyGroup):
    stt_name: bpy.props.StringProperty(name="Name")
    stt_select: bpy.props.BoolProperty(name="Select", default=False, update=lambda self, context: stt_recalculate_shapekeys(self, context))

class STT_ShapekeyTransferProperties(bpy.types.PropertyGroup):
    stt_source_object: bpy.props.PointerProperty(name="Source Object", type=bpy.types.Object, update=lambda self, context: stt_update_shapekeys_list(self, context))
    stt_target_object: bpy.props.PointerProperty(name="Target Object", type=bpy.types.Object)
    stt_all_shapekeys: bpy.props.BoolProperty(name="All Shapekeys", default=True, update=lambda self, context: stt_recalculate_shapekeys(self, context))
    stt_selected_shapekeys: bpy.props.CollectionProperty(type=STT_ShapekeyItem)
    stt_preview: bpy.props.BoolProperty(name="Preview", default=False, update=lambda self, context: stt_update_preview(self, context))
    stt_update_trigger: bpy.props.BoolProperty(name="Update Trigger", default=False, update=lambda self, context: stt_update_shapekeys_list(self, context))

    stt_original_positions: bpy.props.CollectionProperty(type=STT_OriginalPosition)
    stt_original_shapekeys: bpy.props.CollectionProperty(type=STT_OriginalShapeKey)

    def stt_update_selected_shapekeys(self):
        print("Updating selected shapekeys")
        self.stt_update_trigger = not self.stt_update_trigger

def stt_save_original_state(target_obj):
    """Сохраняем оригинальное состояние целевого объекта"""
    print("Saving original state")
    props = bpy.context.scene.stt_shapekey_transfer_props

    if not target_obj or target_obj.type != 'MESH':
        print("No target object or not a mesh")
        return

    shape_keys = target_obj.data.shape_keys
    if not shape_keys:
        print("No shape keys found")
        return

    props.stt_original_positions.clear()
    props.stt_original_shapekeys.clear()

    for vert in target_obj.data.vertices:
        pos = props.stt_original_positions.add()
        pos.x = vert.co.x
        pos.y = vert.co.y
        pos.z = vert.co.z

    for key_block in shape_keys.key_blocks:
        shape_key_item = props.stt_original_shapekeys.add()
        shape_key_item.name = key_block.name
        shape_key_item.value = key_block.value
        for v in key_block.data:
            pos = shape_key_item.values.add()
            pos.x = v.co.x
            pos.y = v.co.y
            pos.z = v.co.z

    print("Original state saved")

def stt_restore_original_state(target_obj):
    """Восстанавливаем оригинальное состояние целевого объекта"""
    global disable_update
    props = bpy.context.scene.stt_shapekey_transfer_props

    if disable_update:
        print("Update is disabled, skipping restoration")
        return

    print("Restoring original state")

    if not target_obj or target_obj.type != 'MESH':
        print("No target object or not a mesh")
        return

    shape_keys = target_obj.data.shape_keys

    if shape_keys:
        key_blocks = list(shape_keys.key_blocks)
        for key_block in key_blocks:
            target_obj.shape_key_remove(key_block)

    for shape_key_item in props.stt_original_shapekeys:
        new_key = target_obj.shape_key_add(name=shape_key_item.name)
        new_key.value = shape_key_item.value
        for i, vert in enumerate(new_key.data):
            orig_pos = shape_key_item.values[i]
            vert.co = Vector((orig_pos.x, orig_pos.y, orig_pos.z))

    for i, vert in enumerate(target_obj.data.vertices):
        orig_pos = props.stt_original_positions[i]
        vert.co = Vector((orig_pos.x, orig_pos.y, orig_pos.z))

    print("Original state restored")

def stt_update_shapekeys_list(self, context):
    """Обновляет список блендшейпов"""
    print("Updating shapekeys list")
    stt_props = context.scene.stt_shapekey_transfer_props
    if stt_props.stt_source_object:
        stt_shape_keys = stt_props.stt_source_object.data.shape_keys
        if stt_shape_keys:
            stt_props.stt_selected_shapekeys.clear()
            for key_block in stt_shape_keys.key_blocks:
                if key_block.name != 'Basis':
                    item = stt_props.stt_selected_shapekeys.add()
                    item.stt_name = key_block.name
    print("Shapekeys list updated")

def stt_update_preview(self, context):
    """Обновляет состояние превью"""
    print("Updating preview")
    stt_props = context.scene.stt_shapekey_transfer_props
    if self.stt_preview:
        stt_save_original_state(stt_props.stt_target_object)
        bpy.ops.object.stt_transfer_shapekeys('INVOKE_DEFAULT')
    else:
        stt_restore_original_state(stt_props.stt_target_object)
    print("Preview updated")

def stt_recalculate_shapekeys(self, context):
    """Пересчитывает блендшейпы"""
    print("Recalculating shapekeys")
    stt_props = context.scene.stt_shapekey_transfer_props
    if stt_props.stt_preview:
        stt_restore_original_state(stt_props.stt_target_object)
        bpy.ops.object.stt_transfer_shapekeys('INVOKE_DEFAULT')
    print("Shapekeys recalculated")

class STT_TransferShapekeysOperator(bpy.types.Operator):
    bl_idname = "object.stt_transfer_shapekeys"
    bl_label = "Transfer Shapekeys"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Выполняет перенос блендшейпов"""
        print("Executing transfer shapekeys")
        stt_props = context.scene.stt_shapekey_transfer_props
        stt_source_obj = stt_props.stt_source_object
        stt_target_obj = stt_props.stt_target_object

        if not stt_source_obj or not stt_target_obj:
            self.report({'ERROR'}, "Source and Target objects must be set")
            return {'CANCELLED'}

        if stt_source_obj.type != 'MESH' or stt_target_obj.type != 'MESH':
            self.report({'ERROR'}, "Source and Target must be mesh objects")
            return {'CANCELLED'}

        stt_source_mesh = stt_source_obj.data
        stt_target_mesh = stt_target_obj.data

        if not stt_source_mesh.shape_keys:
            self.report({'ERROR'}, "Source object has no shapekeys")
            return {'CANCELLED'}

        stt_source_shape_keys = stt_source_mesh.shape_keys.key_blocks
        if not stt_target_mesh.shape_keys:
            stt_target_obj.shape_key_add(name="Basis")

        stt_selected_shapekeys = [item.stt_name for item in stt_props.stt_selected_shapekeys if item.stt_select]

        for key_block in stt_source_shape_keys:
            if key_block.name == 'Basis' or (not stt_props.stt_all_shapekeys and key_block.name not in stt_selected_shapekeys):
                continue

            new_key = stt_target_mesh.shape_keys.key_blocks.get(key_block.name)
            if not new_key:
                new_key = stt_target_obj.shape_key_add(name=key_block.name)
            new_key.value = 0.0

            for target_vert in stt_target_mesh.vertices:
                weights = []
                deltas = []
                for source_vert in stt_source_mesh.vertices:
                    distance = (target_vert.co - source_vert.co).length
                    weight = 1.0 / max(distance, 1e-6)
                    if weight > 0.1:
                        delta = stt_source_shape_keys[key_block.name].data[source_vert.index].co - source_vert.co
                        weights.append(weight)
                        deltas.append(delta)
                
                if weights:
                    total_weight = sum(weights)
                    normalized_weights = [w / total_weight for w in weights]

                    final_delta = Vector((0.0, 0.0, 0.0))
                    for weight, delta in zip(normalized_weights, deltas):
                        final_delta += delta * weight

                    new_key.data[target_vert.index].co = target_vert.co + final_delta

        self.report({'INFO'}, "Shapekeys transferred successfully")
        print("Shapekeys transferred successfully")
        return {'FINISHED'}

class STT_RestoreOriginalShapekeysOperator(bpy.types.Operator):
    bl_idname = "object.stt_restore_original_shapekeys"
    bl_label = "Restore Original Shapekeys"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        """Восстанавливает оригинальные блендшейпы"""
        print("Restoring original shapekeys")
        stt_props = context.scene.stt_shapekey_transfer_props
        stt_target_obj = stt_props.stt_target_object

        if not stt_target_obj or stt_target_obj.type != 'MESH':
            self.report({'ERROR'}, "Target object is not set or not a mesh")
            return {'CANCELLED'}

        stt_restore_original_state(stt_target_obj)

        self.report({'INFO'}, "Shapekeys restored to original")
        print("Shapekeys restored to original")
        return {'FINISHED'}

class STT_UpdateShapekeysListOperator(bpy.types.Operator):
    bl_idname = "object.stt_update_shapekeys_list"
    bl_label = "Update Shapekeys List"
    
    def execute(self, context):
        """Обновляет список блендшейпов"""
        print("Updating shapekeys list")
        stt_update_shapekeys_list(context.scene.stt_shapekey_transfer_props, context)
        self.report({'INFO'}, "Shapekeys list updated")
        print("Shapekeys list updated")
        return {'FINISHED'}

class STT_ShapekeyTransferPanel(bpy.types.Panel):
    bl_label = "Shapekey Transfer"
    bl_idname = "OBJECT_PT_shapekey_transfer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ET'

    def draw(self, context):
        """Рисует панель интерфейса для переноса блендшейпов"""
        layout = self.layout
        scene = context.scene
        stt_props = scene.stt_shapekey_transfer_props

        layout.prop_search(stt_props, "stt_source_object", context.scene, "objects", text="Source Object")
        layout.prop_search(stt_props, "stt_target_object", context.scene, "objects", text="Target Object")
        layout.operator("object.stt_update_shapekeys_list", text="Update Shapekeys List")

        # Отключаем возможность выбора объектов при активном превью
        layout.enabled = not stt_props.stt_preview
        layout.prop(stt_props, "stt_all_shapekeys")
        layout.enabled = True  # Включаем остальные элементы

        if not stt_props.stt_all_shapekeys:
            for item in stt_props.stt_selected_shapekeys:
                row = layout.row()
                row.prop(item, "stt_select", text=item.stt_name)

        layout.prop(stt_props, "stt_preview", toggle=True, text="Preview")
        layout.operator("object.stt_transfer_shapekeys", text="Apply")

def stt_reset_preview():
    """Сбрасывает состояние превью при регистрации плагина без вызова обработчика"""
    global disable_update
    props = bpy.context.scene.stt_shapekey_transfer_props
    disable_update = True
    props.stt_preview = False
    disable_update = False

classes = (
    STT_OriginalPosition,
    STT_OriginalShapeKey,
    STT_ShapekeyItem,
    STT_ShapekeyTransferProperties,
    STT_TransferShapekeysOperator,
    STT_RestoreOriginalShapekeysOperator,
    STT_UpdateShapekeysListOperator,
    STT_ShapekeyTransferPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.stt_shapekey_transfer_props = bpy.props.PointerProperty(type=STT_ShapekeyTransferProperties)
    bpy.app.timers.register(stt_reset_preview)
    print("Shapekey Transfer Tool registered")

def unregister():
    del bpy.types.Scene.stt_shapekey_transfer_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("Shapekey Transfer Tool unregistered")

if __name__ == "__main__":
    register()
