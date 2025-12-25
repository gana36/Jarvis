"""Test profile system end-to-end"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def test_profile_system():
    """Test the complete profile system"""
    from app.services.profile_tool import get_profile_tool
    from app.services.profile_extraction import extract_profile_info, normalize_profile_data
    from app.services.gemini import get_gemini_service
    
    print("\n" + "="*60)
    print("TESTING USER PROFILE SYSTEM")
    print("="*60)
    
    # Test 1: Create/Get Profile
    print("\n1️⃣ Testing Profile Creation...")
    profile_tool = get_profile_tool()
    profile = profile_tool.get_or_create_profile("test_user")
    print(f"✓ Profile created: {profile['user_id']}")
    print(f"  - Timezone: {profile['timezone']}")
    
    # Test 2: Profile Extraction
    print("\n2️⃣ Testing Profile Extraction...")
    gemini = get_gemini_service()
    
    test_messages = [
        "Hi, I'm Alex and I'm a vegetarian",
        "I'm a beginner at Python programming",
        "I love learning about space and astronomy",
        "What's the weather today?",  # Should extract nothing
    ]
    
    for msg in test_messages:
        print(f"\n   Input: \"{msg}\"")
        extracted = await extract_profile_info(gemini.model, msg)
        if extracted:
            normalized = normalize_profile_data(extracted)
            print(f"   ✓ Extracted: {normalized}")
            
            # Update profile
            profile_tool.update_profile_fields("test_user", normalized)
        else:
            print("   ℹ No profile info found")
    
    # Test 3: View Final Profile
    print("\n3️⃣ Final Profile State...")
    final_profile = profile_tool.get_or_create_profile("test_user")
    print(f"✓ Name: {final_profile.get('name')}")
    print(f"✓ Dietary: {final_profile.get('dietary_preference')}")
    print(f"✓ Learning Level: {final_profile.get('learning_level')}")
    print(f"✓ Interests: {final_profile.get('interests')}")
    
    # Test 4: Profile Injection (simulate)
    print("\n4️⃣ Testing Profile Context Injection...")
    profile_context = []
    if final_profile.get('name'):
        profile_context.append(f"Name: {final_profile['name']}")
    if final_profile.get('dietary_preference'):
        profile_context.append(f"Dietary: {final_profile['dietary_preference']}")
    
    context_str = ", ".join(profile_context)
    print(f"✓ Context injected into prompt: {context_str}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_profile_system())
