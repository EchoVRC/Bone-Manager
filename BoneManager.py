bl_info = {
    "name": "Bone Manager",
    "author": "EchoVRC",
    "version": (1, 1),
    "blender": (3, 3, 0),
    "location": "View3D > UI",
    "description": "Manage bone visibility and other properties",
    "warning": "",
    "wiki_url": "",
    "category": "3D View",
}

import bpy
import numpy as np
import bmesh
import mathutils

class UVToolPanel(bpy.types.Panel):
    bl_label = "UV Tools"
    bl_idname = "UV_PT_tools"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'BM'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.operator("uv.straighten_uv_operator", text="Straighten UVs")

class BoneManager(bpy.types.Panel):
    bl_label = "Bone Manager by EchoVRC"
    bl_idname = "OBJECT_PT_bone_manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BM"

    def draw(self, context):
        layout = self.layout
        space = context.space_data

        self.draw_custom_header(layout)
        self.draw_toggle_buttons(layout, space)
        self.draw_actions(layout)
        self.draw_statistics(layout)

    def draw_custom_header(self, layout):
        row = layout.row()
        row.label(text="Use hotkey: alt + Y")

    def draw_toggle_buttons(self, layout, space):
        row = layout.row()
        row.prop(space.overlay, "show_bones", toggle=True, icon='BONE_DATA')
        row = layout.row()
        row.prop(space.overlay, "show_cursor", toggle=True, icon='PIVOT_CURSOR')
        row.prop(space.overlay, "show_edge_crease", toggle=True, icon='EDGESEL')

    def draw_actions(self, layout):
        box = layout.box()
        box.label(text="Playbooks:")
        actions = [
            ("view3d.delete_unused_blendshape", "Delete unused blendshape"),
            ("view3d.delete_unused_vertex_groups", "Delete unused vertex groups"),
            ("view3d.delete_unused_bones", "Delete unused bones"),
            ("view3d.remove_shapekey_influence", "Remove Shapekey Influence"),
            ("view3d.delete_uv_vertices", "Delete Selected UV Vertices"),
            ("view3d.smooth_weights_3d", "Smooth Weights 3D"),
            ("view3d.make_single_user", "Make Single User"),
        ]
        for op_id, op_desc in actions:
            row = box.row()
            row.operator(op_id, text=op_desc)
            if op_id == "view3d.delete_unused_blendshape":
                row = box.row()
                row.label(text="(Don't forget check vrc.sil)")

    def draw_statistics(self, layout):
        total_meshes, total_materials = self.calculate_statistics()
        layout.label(text=f"Meshes: {total_meshes}")
        layout.label(text=f"Materials: {total_materials}")
        layout.label(text="My discord: echovrc")

    @staticmethod
    def calculate_statistics():
        total_meshes = sum(1 for obj in bpy.data.objects if obj.type == 'MESH' and obj.visible_get())
        total_materials = sum(len(obj.material_slots) for obj in bpy.data.objects if obj.type == 'MESH' and obj.visible_get())
        return total_meshes, total_materials

class MakeSingleUser(bpy.types.Operator):
    bl_idname = "view3d.make_single_user"
    bl_label = "Make Single User"
    bl_description = "Make selected objects single user"

    def execute(self, context):
        bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)
        return {'FINISHED'}

class SmoothWeights3D(bpy.types.Operator):
    bl_idname = "view3d.smooth_weights_3d"
    bl_label = "Smooth Weights 3D"
    bl_description = "Smooth vertex group weights based on 3D position"
    
    radius: bpy.props.FloatProperty(name="Radius", default=0.1, min=0.01, max=10.0)
    influence: bpy.props.FloatProperty(name="Influence", default=0.5, min=0.0, max=1.0)
    iterations: bpy.props.IntProperty(name="Iterations", default=1, min=1, max=100)
    
    def execute(self, context):
        obj = bpy.context.object
        for _ in range(self.iterations):
            smooth_weights_3d_global(obj, self.radius, self.influence)
        return {'FINISHED'}

def smooth_weights_3d_global(obj, radius=0.1, influence=0.5):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    
    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()
    
    vertex_layers = bm.verts.layers.deform.verify()
    
    for vert in bm.verts:
        if not vert[vertex_layers]:  # Skip vertices without weights
            continue

        weights = {}
        total_count = 0

        for (co, index, dist) in kd.find_range(vert.co, radius):
            v = bm.verts[index]
            for group, weight in v[vertex_layers].items():
                weights[group] = weights.get(group, 0) + weight
                total_count += 1

        if total_count == 0:
            continue

        for group, weight in weights.items():
            vert[vertex_layers][group] = (1.0 - influence) * vert[vertex_layers].get(group, 0) + (influence * weight / total_count)

    bm.to_mesh(mesh)
    bm.free()

class DeleteSelectedUVVertices:
    @staticmethod
    def execute():
        obj = bpy.context.object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        uv_layer = bm.loops.layers.uv.verify()

        for face in bm.faces:
            for loop in face.loops:
                uv_data = loop[uv_layer]
                if uv_data.select:
                    uv_data.uv = (0, 0)

        bmesh.update_edit_mesh(me)

class DeleteUVVerticesOperator(bpy.types.Operator):
    bl_idname = "view3d.delete_uv_vertices"
    bl_label = "Delete Selected UV Vertices"
    
    def execute(self, context):
        DeleteSelectedUVVertices.execute()
        return {'FINISHED'}

class DeleteUnusedBones(bpy.types.Operator):
    bl_idname = "view3d.delete_unused_bones"
    bl_label = "Delete Unused Bones"
    bl_description = "Deletes all unused bones from the selected armature"

    vertex_group_names = set()

    @classmethod
    def is_bone_or_child_used(cls, bone):
        if bone.name in cls.vertex_group_names:
            return True

        return False

    def execute(self, context):
        for ob in bpy.context.selected_objects:
            if ob.type != 'ARMATURE': continue

            armature = ob.data
            bones_to_delete = set(armature.bones.keys())

            mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == ob]

            self.vertex_group_names.clear()
            for mesh_obj in mesh_objects:
                self.vertex_group_names.update(vg.name for vg in mesh_obj.vertex_groups)

            for bone in armature.bones:
                if self.is_bone_or_child_used(bone):
                    bones_to_delete.discard(bone.name)
                    parent = bone.parent
                    while parent:
                        bones_to_delete.discard(parent.name)
                        parent = parent.parent

            print(bones_to_delete)
            bpy.ops.object.mode_set(mode='EDIT')
            for bone_name in bones_to_delete:
                if bone_name in armature.edit_bones:
                    edit_bone = armature.edit_bones[bone_name]
                    armature.edit_bones.remove(edit_bone)
            bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

class ToggleBoneVisibility(bpy.types.Operator):
    bl_idname = "view3d.toggle_bone_visibility"
    bl_label = "Toggle Bone Visibility"

    def execute(self, context):
        context.space_data.overlay.show_bones = not context.space_data.overlay.show_bones
        return {'FINISHED'}
        
class DeleteUnusedVertexGroups(bpy.types.Operator):
    bl_idname = "view3d.delete_unused_vertex_groups"
    bl_label = "Delete Unused Vertex Groups"
    bl_description = "Deletes all unused vertex groups from the selected object"

    def execute(self, context):
        for ob in bpy.context.selected_objects:
            if ob.type != 'MESH': continue

            to_delete = []

            for group in ob.vertex_groups:
                if not any(v.groups and any(g.group == group.index for g in v.groups) for v in ob.data.vertices):
                    to_delete.append(group.name)

            for group_name in to_delete:
                ob.vertex_groups.remove(ob.vertex_groups[group_name])

        return {'FINISHED'}

class DeleteUnusedBlendshape(bpy.types.Operator):
    bl_idname = "view3d.delete_unused_blendshape"
    bl_label = "Delete Unused Blendshape"
    bl_description = "Deletes all unused blendshapes from the selected object"

    def execute(self, context):
        tolerance = 0.001
        for ob in bpy.context.selected_objects:
            if ob.type != 'MESH': continue
            if not ob.data.shape_keys: continue
            if not ob.data.shape_keys.use_relative: continue

            kbs = ob.data.shape_keys.key_blocks
            nverts = len(ob.data.vertices)
            to_delete = []

            cache = {}
            locs = np.empty(3*nverts, dtype=np.float32)

            for kb in kbs:
                if kb.name == "Basis": continue  # Skip Basis

                kb.data.foreach_get("co", locs)

                if kb.relative_key.name not in cache:
                    rel_locs = np.empty(3*nverts, dtype=np.float32)
                    kb.relative_key.data.foreach_get("co", rel_locs)
                    cache[kb.relative_key.name] = rel_locs
                rel_locs = cache[kb.relative_key.name]

                locs -= rel_locs
                if (np.abs(locs) < tolerance).all():
                    to_delete.append(kb.name)

            for kb_name in to_delete:
                ob.shape_key_remove(ob.data.shape_keys.key_blocks[kb_name])

        return {'FINISHED'}

def straighten_uv():
    obj = bpy.context.active_object
    if obj and obj.type == 'MESH':
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active

        if not uv_layer:
            print("No active UV layer found")
            return

        selected_uv_coords = []
        selected_uv_loops = []

        for face in bm.faces:
            for loop in face.loops:
                if loop[uv_layer].select:
                    selected_uv_coords.append(loop[uv_layer].uv.copy())
                    selected_uv_loops.append(loop)

        unique_selected_uv_coords = np.unique(np.array(selected_uv_coords), axis=0)

        if len(unique_selected_uv_coords) != 4:
            print("Number of unique selected UV vertices is not 4:", len(unique_selected_uv_coords))
            return

        min_x, min_y = np.min(unique_selected_uv_coords, axis=0)
        max_x, max_y = np.max(unique_selected_uv_coords, axis=0)

        aligned_uv = np.array([
            [min_x, min_y],
            [min_x, max_y],
            [max_x, max_y],
            [max_x, min_y]
        ])

        for loop in selected_uv_loops:
            closest_aligned_uv = aligned_uv[np.argmin(np.linalg.norm(aligned_uv - loop[uv_layer].uv, axis=1))]
            loop[uv_layer].uv = closest_aligned_uv

        bmesh.update_edit_mesh(obj.data)
        print("UV straightened")

class StraightenUVOperator(bpy.types.Operator):
    bl_idname = "uv.straighten_uv_operator"
    bl_label = "Straighten UVs"

    def execute(self, context):
        straighten_uv()
        return {'FINISHED'}

class RemoveShapeKeyInfluence(bpy.types.Operator):
    bl_idname = "view3d.remove_shapekey_influence"
    bl_label = "Remove Shapekey Influence"
    bl_description = "Removes the influence of the active shapekey from selected vertices"

    def execute(self, context):
        obj = bpy.context.object
        mesh = obj.data

        if not mesh.shape_keys:
            self.report({'WARNING'}, "No shape keys on object.")
            return {'CANCELLED'}
        
        active_key_index = obj.active_shape_key_index
        
        if active_key_index > 0:
            active_key = mesh.shape_keys.key_blocks[active_key_index]
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            for vert in mesh.vertices:
                if vert.select:
                    active_key.data[vert.index].co = mesh.vertices[vert.index].co
            
            bpy.ops.object.mode_set(mode='EDIT')
            
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No active shape key selected.")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(BoneManager)
    bpy.utils.register_class(DeleteUVVerticesOperator)
    bpy.utils.register_class(ToggleBoneVisibility)
    bpy.utils.register_class(DeleteUnusedBlendshape)
    bpy.utils.register_class(DeleteUnusedVertexGroups)
    bpy.utils.register_class(StraightenUVOperator)
    bpy.utils.register_class(UVToolPanel)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='3D View Generic', space_type='VIEW_3D')
    kmi = km.keymap_items.new(ToggleBoneVisibility.bl_idname, 'Y', 'PRESS', alt=True)
    bpy.utils.register_class(DeleteUnusedBones)
    bpy.utils.register_class(RemoveShapeKeyInfluence)
    bpy.utils.register_class(SmoothWeights3D)
    bpy.utils.register_class(MakeSingleUser)
    

def unregister():
    bpy.utils.unregister_class(BoneManager)
    bpy.utils.unregister_class(DeleteUVVerticesOperator)
    bpy.utils.unregister_class(ToggleBoneVisibility)
    bpy.utils.unregister_class(DeleteUnusedBlendshape)
    bpy.utils.unregister_class(DeleteUnusedVertexGroups)
    bpy.utils.unregister_class(DeleteUnusedBones)
    bpy.utils.unregister_class(RemoveShapeKeyInfluence)
    bpy.utils.unregister_class(SmoothWeights3D)
    bpy.utils.unregister_class(MakeSingleUser)
    bpy.utils.unregister_class(StraightenUVOperator)
    bpy.utils.unregister_class(UVToolPanel)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps['3D View Generic']
    for kmi in km.keymap_items:
        if kmi.idname == ToggleBoneVisibility.bl_idname:
            km.keymap_items.remove(kmi)

if __name__ == "__main__":
    register()