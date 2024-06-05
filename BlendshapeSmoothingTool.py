bl_info = {
    "name": "Blendshape Smoothing Tool",
    "author": "EchoVRC",
    "blender": (3, 3, 0),
    "version": (1, 1),
    "description": "Tool for smoothing blendshapes",
    "location": "View3D > UI",
    "category": "3D View"
}

import bpy
import bmesh
from mathutils import Vector

# Глобальная переменная для управления обновлениями
bst_disable_update = False

class BST_BlendShapeItem(bpy.types.PropertyGroup):
    bst_name: bpy.props.StringProperty(name="Name")
    bst_select: bpy.props.BoolProperty(name="Select", default=False, update=lambda self, context: bst_update_select(self, context))

class BST_VertexPosition(bpy.types.PropertyGroup):
    bst_x: bpy.props.FloatProperty(name="X")
    bst_y: bpy.props.FloatProperty(name="Y")
    bst_z: bpy.props.FloatProperty(name="Z")

class BST_BlendShapeProperties(bpy.types.PropertyGroup):
    bst_all_blendshapes: bpy.props.BoolProperty(name="All Blendshapes", default=True, update=lambda self, context: bst_update_all_blendshapes(self, context))
    bst_iterations: bpy.props.IntProperty(name="Iterations", default=1, min=1, max=10, update=lambda self, context: bst_update_iterations(self, context))
    bst_preview: bpy.props.BoolProperty(name="Preview", default=False, update=lambda self, context: bst_update_preview(self, context))
    bst_selected_blendshapes: bpy.props.CollectionProperty(type=BST_BlendShapeItem)
    bst_original_positions: bpy.props.CollectionProperty(type=BST_VertexPosition)
    bst_selected_object: bpy.props.PointerProperty(name="Selected Object", type=bpy.types.Object)
    bst_strength: bpy.props.FloatProperty(name="Strength", default=0.5, min=0.0, max=1.0, update=lambda self, context: bst_update_strength(self, context))

def bst_update_select(self, context):
    global bst_disable_update
    if bst_disable_update:
        return
    props = context.scene.bst_blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.bst_preview:
            bpy.ops.object.bst_restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.bst_smooth_blendshapes('INVOKE_DEFAULT')

def bst_update_all_blendshapes(self, context):
    global bst_disable_update
    if bst_disable_update:
        return
    props = context.scene.bst_blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.bst_all_blendshapes and props.bst_preview:
            bpy.ops.object.bst_restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.bst_smooth_blendshapes('INVOKE_DEFAULT')

def bst_update_iterations(self, context):
    global bst_disable_update
    if bst_disable_update:
        return
    props = context.scene.bst_blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.bst_preview:
            bpy.ops.object.bst_restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.bst_smooth_blendshapes('INVOKE_DEFAULT')

def bst_update_strength(self, context):
    global bst_disable_update
    if bst_disable_update:
        return
    props = context.scene.bst_blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.bst_preview:
            bpy.ops.object.bst_restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.bst_smooth_blendshapes('INVOKE_DEFAULT')

def bst_update_preview(self, context):
    global bst_disable_update
    if bst_disable_update:
        return
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if self.bst_preview:
            bpy.ops.object.bst_save_original_values('INVOKE_DEFAULT')
            bpy.ops.object.bst_smooth_blendshapes('INVOKE_DEFAULT')
        else:
            bpy.ops.object.bst_restore_original_values('INVOKE_DEFAULT')

class BST_SaveOriginalValuesOperator(bpy.types.Operator):
    bl_idname = "object.bst_save_original_values"
    bl_label = "Save Original Values"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        props = context.scene.bst_blendshape_props
        obj = props.bst_selected_object

        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        shape_keys = obj.data.shape_keys
        if not shape_keys:
            return {'CANCELLED'}

        props.bst_original_positions.clear()

        for key_block in shape_keys.key_blocks:
            for v in key_block.data:
                pos = props.bst_original_positions.add()
                pos.bst_x = v.co.x
                pos.bst_y = v.co.y
                pos.bst_z = v.co.z

        return {'FINISHED'}

class BST_RestoreOriginalValuesOperator(bpy.types.Operator):
    bl_idname = "object.bst_restore_original_values"
    bl_label = "Restore Original Values"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        props = context.scene.bst_blendshape_props
        obj = props.bst_selected_object

        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        shape_keys = obj.data.shape_keys
        if not shape_keys or not props.bst_original_positions:
            return {'CANCELLED'}

        index = 0
        for key_block in shape_keys.key_blocks:
            for vert in key_block.data:
                orig_pos = props.bst_original_positions[index]
                vert.co = Vector((orig_pos.bst_x, orig_pos.bst_y, orig_pos.bst_z))
                index += 1

        return {'FINISHED'}

class BST_UpdateBlendShapesOperator(bpy.types.Operator):
    bl_idname = "object.bst_update_blendshapes"
    bl_label = "Update Blendshapes"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        props = context.scene.bst_blendshape_props
        obj = props.bst_selected_object

        if not obj or obj.type != 'MESH' or not obj.data.shape_keys:
            return {'CANCELLED'}

        shape_keys = obj.data.shape_keys.key_blocks

        props.bst_selected_blendshapes.clear()
        for key_block in shape_keys:
            if key_block.name != 'Basis':
                item = props.bst_selected_blendshapes.add()
                item.bst_name = key_block.name

        return {'FINISHED'}

class BST_SmoothBlendShapesOperator(bpy.types.Operator):
    bl_idname = "object.bst_smooth_blendshapes"
    bl_label = "Smooth Blendshapes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.bst_blendshape_props
        obj = props.bst_selected_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}

        # Получение всех shape keys
        shape_keys = obj.data.shape_keys
        if not shape_keys:
            self.report({'ERROR'}, "No shape keys found")
            return {'CANCELLED'}

        basis_key = shape_keys.key_blocks['Basis']

        selected_keys = [item.bst_name for item in props.bst_selected_blendshapes if item.bst_select]

        # Перебор всех shape keys для сглаживания
        for key_block in shape_keys.key_blocks:
            if key_block.name != 'Basis' and (props.bst_all_blendshapes or key_block.name in selected_keys):
                self.smooth_shape_key(obj, basis_key, key_block, props.bst_iterations, props.bst_strength)

        self.report({'INFO'}, "Blendshapes smoothed successfully")
        return {'FINISHED'}

    def smooth_shape_key(self, obj, basis_key, key_block, iterations, strength):
        # Получение данных shape key
        key_verts = key_block.data
        basis_verts = basis_key.data

        for _ in range(iterations):
            new_offsets = [Vector((0, 0, 0))] * len(key_verts)

            bm = bmesh.new()
            bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
            bm.verts.ensure_lookup_table()

            for vert in bm.verts:
                basis_co = basis_verts[vert.index].co
                key_co = key_verts[vert.index].co
                offset = key_co - basis_co

                neighbor_offsets = [offset]
                for edge in vert.link_edges:
                    neighbor_vert = edge.other_vert(vert)
                    neighbor_basis_co = basis_verts[neighbor_vert.index].co
                    neighbor_key_co = key_verts[neighbor_vert.index].co
                    neighbor_offset = neighbor_key_co - neighbor_basis_co
                    neighbor_offsets.append(neighbor_offset)

                avg_offset = sum(neighbor_offsets, Vector()) / len(neighbor_offsets)
                new_offsets[vert.index] = offset.lerp(avg_offset, strength)

            for i, offset in enumerate(new_offsets):
                key_verts[i].co = basis_verts[i].co + offset

            bm.free()

class BST_BlendShapePanel(bpy.types.Panel):
    bl_label = "Blendshape Smoothing"
    bl_idname = "OBJECT_PT_blendshape_smoothing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ET'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.bst_blendshape_props

        layout.prop_search(props, "bst_selected_object", context.scene, "objects", text="Object")

        if props.bst_selected_object:
            layout.prop(props, "bst_all_blendshapes")

            if not props.bst_all_blendshapes:
                layout.operator("object.bst_update_blendshapes", text="Refresh Blendshapes List")
                for item in props.bst_selected_blendshapes:
                    row = layout.row()
                    row.prop(item, "bst_select", text=item.bst_name)

            layout.prop(props, "bst_iterations")
            layout.prop(props, "bst_strength")
            layout.prop(props, "bst_preview", toggle=True, text="Preview")
            layout.operator("object.bst_smooth_blendshapes", text="Apply")

def register():
    bpy.utils.register_class(BST_BlendShapeItem)
    bpy.utils.register_class(BST_VertexPosition)
    bpy.utils.register_class(BST_BlendShapeProperties)
    bpy.utils.register_class(BST_SaveOriginalValuesOperator)
    bpy.utils.register_class(BST_RestoreOriginalValuesOperator)
    bpy.utils.register_class(BST_UpdateBlendShapesOperator)
    bpy.utils.register_class(BST_SmoothBlendShapesOperator)
    bpy.utils.register_class(BST_BlendShapePanel)
    bpy.types.Scene.bst_blendshape_props = bpy.props.PointerProperty(type=BST_BlendShapeProperties)
    bpy.app.timers.register(bst_reset_preview)

def unregister():
    bpy.utils.unregister_class(BST_BlendShapeItem)
    bpy.utils.unregister_class(BST_VertexPosition)
    bpy.utils.unregister_class(BST_BlendShapeProperties)
    bpy.utils.unregister_class(BST_SaveOriginalValuesOperator)
    bpy.utils.unregister_class(BST_RestoreOriginalValuesOperator)
    bpy.utils.unregister_class(BST_UpdateBlendShapesOperator)
    bpy.utils.unregister_class(BST_SmoothBlendShapesOperator)
    bpy.utils.unregister_class(BST_BlendShapePanel)
    del bpy.types.Scene.bst_blendshape_props

def bst_reset_preview():
    """Сбрасывает состояние превью при регистрации плагина без вызова обработчика"""
    global bst_disable_update
    props = bpy.context.scene.bst_blendshape_props
    bst_disable_update = True
    props.bst_preview = False
    bst_disable_update = False

if __name__ == "__main__":
    register()
