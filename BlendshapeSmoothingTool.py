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

class BlendShapeItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    select: bpy.props.BoolProperty(name="Select", default=False, update=lambda self, context: update_select(self, context))

class VertexPosition(bpy.types.PropertyGroup):
    x: bpy.props.FloatProperty(name="X")
    y: bpy.props.FloatProperty(name="Y")
    z: bpy.props.FloatProperty(name="Z")

class BlendShapeProperties(bpy.types.PropertyGroup):
    all_blendshapes: bpy.props.BoolProperty(name="All Blendshapes", default=True, update=lambda self, context: update_all_blendshapes(self, context))
    iterations: bpy.props.IntProperty(name="Iterations", default=1, min=1, max=10, update=lambda self, context: update_iterations(self, context))
    preview: bpy.props.BoolProperty(name="Preview", default=False, update=lambda self, context: update_preview(self, context))
    selected_blendshapes: bpy.props.CollectionProperty(type=BlendShapeItem)
    original_positions: bpy.props.CollectionProperty(type=VertexPosition)
    selected_object: bpy.props.PointerProperty(name="Selected Object", type=bpy.types.Object)
    strength: bpy.props.FloatProperty(name="Strength", default=0.5, min=0.0, max=1.0, update=lambda self, context: update_strength(self, context))

def update_select(self, context):
    props = context.scene.blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.preview:
            bpy.ops.object.restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.smooth_blendshapes('INVOKE_DEFAULT')

def update_all_blendshapes(self, context):
    props = context.scene.blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.all_blendshapes and props.preview:
            bpy.ops.object.restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.smooth_blendshapes('INVOKE_DEFAULT')

def update_iterations(self, context):
    props = context.scene.blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.preview:
            bpy.ops.object.restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.smooth_blendshapes('INVOKE_DEFAULT')

def update_strength(self, context):
    props = context.scene.blendshape_props
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if props.preview:
            bpy.ops.object.restore_original_values('INVOKE_DEFAULT')
            bpy.ops.object.smooth_blendshapes('INVOKE_DEFAULT')

def update_preview(self, context):
    if not hasattr(context.scene, 'stt_shapekey_transfer_props') or not context.scene.stt_shapekey_transfer_props.stt_preview:
        if self.preview:
            bpy.ops.object.save_original_values('INVOKE_DEFAULT')
            bpy.ops.object.smooth_blendshapes('INVOKE_DEFAULT')
        else:
            bpy.ops.object.restore_original_values('INVOKE_DEFAULT')

class SaveOriginalValuesOperator(bpy.types.Operator):
    bl_idname = "object.save_original_values"
    bl_label = "Save Original Values"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        props = context.scene.blendshape_props
        obj = props.selected_object

        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        shape_keys = obj.data.shape_keys
        if not shape_keys:
            return {'CANCELLED'}

        props.original_positions.clear()

        for key_block in shape_keys.key_blocks:
            for v in key_block.data:
                pos = props.original_positions.add()
                pos.x = v.co.x
                pos.y = v.co.y
                pos.z = v.co.z

        return {'FINISHED'}

class RestoreOriginalValuesOperator(bpy.types.Operator):
    bl_idname = "object.restore_original_values"
    bl_label = "Restore Original Values"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        props = context.scene.blendshape_props
        obj = props.selected_object

        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        shape_keys = obj.data.shape_keys
        if not shape_keys or not props.original_positions:
            return {'CANCELLED'}

        index = 0
        for key_block in shape_keys.key_blocks:
            for vert in key_block.data:
                orig_pos = props.original_positions[index]
                vert.co = Vector((orig_pos.x, orig_pos.y, orig_pos.z))
                index += 1

        return {'FINISHED'}

class UpdateBlendShapesOperator(bpy.types.Operator):
    bl_idname = "object.update_blendshapes"
    bl_label = "Update Blendshapes"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        props = context.scene.blendshape_props
        obj = props.selected_object

        if not obj or obj.type != 'MESH' or not obj.data.shape_keys:
            return {'CANCELLED'}

        shape_keys = obj.data.shape_keys.key_blocks

        props.selected_blendshapes.clear()
        for key_block in shape_keys:
            if key_block.name != 'Basis':
                item = props.selected_blendshapes.add()
                item.name = key_block.name

        return {'FINISHED'}

class SmoothBlendShapesOperator(bpy.types.Operator):
    bl_idname = "object.smooth_blendshapes"
    bl_label = "Smooth Blendshapes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.blendshape_props
        obj = props.selected_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}

        # Получение всех shape keys
        shape_keys = obj.data.shape_keys
        if not shape_keys:
            self.report({'ERROR'}, "No shape keys found")
            return {'CANCELLED'}

        basis_key = shape_keys.key_blocks['Basis']

        selected_keys = [item.name for item in props.selected_blendshapes if item.select]

        # Перебор всех shape keys для сглаживания
        for key_block in shape_keys.key_blocks:
            if key_block.name != 'Basis' and (props.all_blendshapes or key_block.name in selected_keys):
                self.smooth_shape_key(obj, basis_key, key_block, props.iterations, props.strength)

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

class BlendShapePanel(bpy.types.Panel):
    bl_label = "Blendshape Smoothing"
    bl_idname = "OBJECT_PT_blendshape_smoothing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ET'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.blendshape_props

        layout.prop_search(props, "selected_object", context.scene, "objects", text="Object")

        if props.selected_object:
            layout.prop(props, "all_blendshapes")

            if not props.all_blendshapes:
                layout.operator("object.update_blendshapes", text="Refresh Blendshapes List")
                for item in props.selected_blendshapes:
                    row = layout.row()
                    row.prop(item, "select", text=item.name)

            layout.prop(props, "iterations")
            layout.prop(props, "strength")
            layout.prop(props, "preview", toggle=True, text="Preview")
            layout.operator("object.smooth_blendshapes", text="Apply")

def register():
    bpy.utils.register_class(BlendShapeItem)
    bpy.utils.register_class(VertexPosition)
    bpy.utils.register_class(BlendShapeProperties)
    bpy.utils.register_class(SaveOriginalValuesOperator)
    bpy.utils.register_class(RestoreOriginalValuesOperator)
    bpy.utils.register_class(UpdateBlendShapesOperator)
    bpy.utils.register_class(SmoothBlendShapesOperator)
    bpy.utils.register_class(BlendShapePanel)
    bpy.types.Scene.blendshape_props = bpy.props.PointerProperty(type=BlendShapeProperties)

def unregister():
    bpy.utils.unregister_class(BlendShapeItem)
    bpy.utils.unregister_class(VertexPosition)
    bpy.utils.unregister_class(BlendShapeProperties)
    bpy.utils.unregister_class(SaveOriginalValuesOperator)
    bpy.utils.unregister_class(RestoreOriginalValuesOperator)
    bpy.utils.unregister_class(UpdateBlendShapesOperator)
    bpy.utils.unregister_class(SmoothBlendShapesOperator)
    bpy.utils.unregister_class(BlendShapePanel)
    del bpy.types.Scene.blendshape_props

if __name__ == "__main__":
    register()
