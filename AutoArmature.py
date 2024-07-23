bl_info = {
    "name": "Auto Armature Select in Weight Paint",
    "blender": (3, 3, 0),
    "category": "Object",
    "author": "EchoVRC"
}

import bpy

class OBJECT_OT_auto_armature_weight_paint(bpy.types.Operator):
    bl_idname = "object.auto_armature_weight_paint"
    bl_label = "Auto Armature for Weight Paint"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object:
                    context.view_layer.objects.active = modifier.object
                    modifier.object.select_set(True)

                    context.view_layer.objects.active = obj
                    obj.select_set(True)

                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
                    print("AAS: Done")
                    break

        return {'FINISHED'}

def auto_armature_weight_paint_handler(scene):
    if  bpy.context.mode != 'PAINT_WEIGHT' and not (bpy.context.mode == 'OBJECT' and getattr(scene, "auto_armature_progress", True)):
        scene.auto_armature_executed = False
        print("AAS: Reset")

    if bpy.context.mode == 'PAINT_WEIGHT' and not getattr(scene, "auto_armature_executed", False):
        scene.auto_armature_executed = True
        scene.auto_armature_progress = True
        print("AAS: Start")
        bpy.ops.object.auto_armature_weight_paint()
        print("AAS: End")
        scene.auto_armature_progress = False

def register():
    bpy.utils.register_class(OBJECT_OT_auto_armature_weight_paint)
    bpy.app.handlers.depsgraph_update_post.append(auto_armature_weight_paint_handler)
    bpy.types.Scene.auto_armature_executed = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.auto_armature_progress = bpy.props.BoolProperty(default=False)
    print("AAS: Loaded")

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_auto_armature_weight_paint)
    bpy.app.handlers.depsgraph_update_post.remove(auto_armature_weight_paint_handler)
    del bpy.types.Scene.auto_armature_executed
    del bpy.types.Scene.auto_armature_progress

if __name__ == "__main__":
    register()
